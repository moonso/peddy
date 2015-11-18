# -*- coding: utf-8 -*-

from __future__ import print_function
import sys
import collections
from collections import OrderedDict, defaultdict
import networkx as nx
from heapq import *

#https://gist.githubusercontent.com/kachayev/5956408/raw/c918417ef7f3c0deb6a0a1223a49035dcca84077/uf.py
class UF(object):
    __slots__ = ('p', 'rank')

    def __init__(self, size):
        self.p = [None]*size
        self.rank = [1]*size

    def make(self, el):
        self.p[el] = el

    def find(self, el):
        if self.p[el] == el: return el
        self.p[el] = self.find(self.p[el])
        return self.p[el]

    def unite(self, l, r):
        li, ri = self.find(l), self.find(r)
        if self.rank[li] < self.rank[ri]:
            self.p[li] = ri
        else:
            self.p[ri] = li
            if self.rank[li] == self.rank[ri]:
                self.rank[li] += 1


# https://github.com/tmr232/Sark/blob/1b1d9a50c23e7a0774a9849137dc80998b1e9c46/sark/graph.py
def lowest_common_ancestors(G, targets):
    common_ancestors = None
    all_ancestors = set()
    for target in targets:
        parents = set()
        q = collections.deque()
        q.append(target)

        while q:
            n = q.popleft()
            if n in parents:
                continue
            for p in G.successors_iter(n):
                q.append(p)
            parents.add(n)

        all_ancestors.update(parents)

        if common_ancestors is None:
            common_ancestors = parents
        else:
            common_ancestors &= parents

    lowest_common = set()
    if common_ancestors is not None:
        for p in common_ancestors:
            if any(child not in common_ancestors and child in all_ancestors for child in G.predecessors_iter(p)):
                lowest_common.add(p)

    return lowest_common

if sys.version_info[0] == 3:
    basestring = str

class UNKNOWN(object):
    def __str__(self):
        return "-9"

class PHENOTYPE(object):
    AFFECTED = True
    UNAFFECTED = False
    UNKNOWN = UNKNOWN()

    @classmethod
    def lookup(cls, i):
        return {'2': cls.AFFECTED, '1': cls.UNAFFECTED}.get(i, cls.UNKNOWN)

    @classmethod
    def rlookup(cls, i):
        return {cls.AFFECTED: 'affected', cls.UNAFFECTED: 'unaffected'}.get(i, cls.UNKNOWN)


class SEX(object):
    MALE = 'male'
    FEMALE = 'female'
    UNKNOWN = UNKNOWN()

    @classmethod
    def lookup(cls, i):
        return {'1': cls.MALE, '2': cls.FEMALE}.get(i, cls.UNKNOWN)

    @classmethod
    def rlookup(cls, i):
        return {cls.MALE: 'male', cls.FEMALE: 'female'}.get(i, cls.UNKNOWN)

UNKNOWN = UNKNOWN()


class Sample(object):

    def __init__(self, family_id, sample_id, paternal_id, maternal_id, sex,
                 phenotype, extra_attrs=None, header=None,
                 missing=('-9', '0', '.')):
        self.family_id = family_id
        self.sample_id = sample_id
        self.dad = None
        self.mom = None
        self.paternal_id = UNKNOWN if paternal_id in missing else paternal_id
        self.maternal_id = UNKNOWN if maternal_id in missing else maternal_id
        if self.paternal_id != UNKNOWN:
            self.dad = self.paternal_id
        if self.maternal_id != UNKNOWN:
            self.mom = self.maternal_id
        self._sex = sex
        self._phenotype = phenotype
        self.sex = SEX.lookup(sex)
        self.affected = PHENOTYPE.lookup(phenotype)
        self.kids = []
        self.header = header
        self.attrs = extra_attrs or []

    def __eq__(self, other):
        if self is None or other is None:
            return False
        return (self.sample_id == other.sample_id) and (self.family_id ==
                                                        other.family_id)
    def __hash__(self):
        return hash((self.sample_id, self.family_id))

    def _get_mom(self):
        return self._mom

    def _set_mom(self, mom):
        if isinstance(mom, Sample):
            if mom.sex == SEX.MALE:
                sys.stderr.write("pedigree warning: '%s' is mom but has male sex\n" % mom.sample_id)
            elif mom.sex == SEX.UNKNOWN:
                sys.stderr.write("pedigree notice: '%s' is mom but has unknown sex. Setting to female\n" % mom.sample_id)

            if mom.family_id != self.family_id:
                sys.stderr.write("pedigree warning: '%s' is mom has different family_id from %s\n" % (mom.sample_id, self.sample_id))

            if mom.sample_id == self.sample_id:
                sys.stderr.write("pedigree warning: '%s' is mom of self\n" % (self.sample_id))

        self._mom = mom

    mom = property(_get_mom, _set_mom)

    def _get_dad(self):
        return self._dad

    def _set_dad(self, dad):
        if isinstance(dad, Sample):
            if dad.sex == SEX.FEMALE:
                sys.stderr.write("pedigree warning: '%s' is dad but has female sex\n" % dad.sample_id)
            elif dad.sex == SEX.UNKNOWN:
                sys.stderr.write("pedigree notice: '%s' is dad but has unknown sex. Setting to male\n" % dad.sample_id)

            if dad.family_id != self.family_id:
                sys.stderr.write("pedigree warning: '%s' is dad has different family_id from %s\n" % (dad.sample_id, self.sample_id))

            if dad.sample_id == self.sample_id:
                sys.stderr.write("pedigree warning: '%s' is dad of self\n" % (self.sample_id))

        self._dad = dad

    dad = property(_get_dad, _set_dad)

    def __repr__(self):
        v = "%s('%s', '%s', '%s', '%s', '%s', '%s'" % (self.__class__.__name__,
                                                       self.family_id,
                                                       self.sample_id,
                                                       self.paternal_id,
                                                       self.maternal_id,
                                                       SEX.rlookup(self.sex),
                                                       PHENOTYPE.rlookup(self.affected))
        if self.attrs:
            v += ", " + str(self.attrs)
        v += ")"
        return v

    def __getattr__(self, key):
        if not key in self.header:
            raise AttributeError(key)
        return self.attrs[self.header.index(key) - 6]


    @property
    def siblings(self):
        sibs = []
        for parent in (self.mom, self.dad):
            if parent is UNKNOWN: continue
            sibs.extend(x for x in parent.kids if x not in sibs and x != self)
        return sibs

    @property
    def full_siblings(self):
        sibs = []

        if self.mom is None or self.dad is None:
            return sibs
        return [s for s in self.mom.kids if s in self.dad.kids and s != self]

    @classmethod
    def from_row(cls, row, header=None):
        if isinstance(row, basestring):
            row = row.strip("\n").split()
        return cls(row[0], row[1], row[2], row[3], row[4], row[5], row[6:],
                   header=header)

    def __str__(self):
        v = "%s %s %s %s %s %s" % (self.family_id, self.sample_id,
                                   self.paternal_id,
                                   self.maternal_id,
                                   self._sex, self._phenotype)
        if self.attrs:
            v += " " + " ".join(self.attrs)
        return v


class Family(object):
    """Family groups samples in the same family.
    A new object is created with a list of `Sample` objects with
    the same `family_id`.
    Iterating over the family gives the samples in the order they were given to
    the constructor.
    """
    def __init__(self, samples):
        assert len(set(s.family_id for s in samples)) == 1
        self.unknown_samples = []
        self.samples = samples
        self._build()
        for u in self.unknown_samples:
            print("unknown sample: %s in family: %s" % (u,
                  samples[0].family_id), file=sys.stderr)

    def __iter__(self):
        self._index = 0
        return self

    def next(self):
        try:
            sample = self.samples[self._index]
        except IndexError:
            raise StopIteration
        self._index += 1
        return sample

    __next__ = next

    def summary(self):
        affection = {PHENOTYPE.AFFECTED: 0, PHENOTYPE.UNAFFECTED: 0,
                     PHENOTYPE.UNKNOWN: 0}
        sex = {SEX.MALE: 0, SEX.FEMALE: 0, SEX.UNKNOWN: 0}

        trios, quads = 0, 0

        for s in self.samples:
            affection[s.affected] += 1
            sex[s.sex] += 1
            if s.mom and s.dad:
                trios += 1
            if list(s.full_siblings):
                quads += 1

        return affection, sex, trios, quads

    @property
    def sib_pairs(self):
        "yield pairs of siblings."
        seen = set()
        for s in self.samples:
            sibs = list(s.full_siblings)
            for sib in sibs:
                if (s.sample_id, sib.sample_id) in seen: continue
                if (sib.sample_id, s.sample_id) in seen: continue
                seen.add((s.sample_id, sib.sample_id))
                yield s, sib

    @property
    def parent_child(self):
        "yield child, parent pairs"
        seen = set()
        for s in self.samples:
            for parent in (p for p in [s.mom, s.dad] if p is not None):
                if (s.sample_id, parent.sample_id) in seen: continue
                if (parent.sample_id, s.sample_id) in seen: continue
                seen.add((s.sample_id, parent.sample_id))
                yield s, parent

    def _build(self):
        by_id = OrderedDict()
        for s in self.samples:
            by_id[s.sample_id] = s
        by_id[None] = None
        for s in self.samples:
            if s.paternal_id != UNKNOWN:
                try:
                    s.dad = by_id[s.paternal_id]
                    s.dad.kids.append(s)
                except KeyError:
                    s.dad = None
                    self.unknown_samples.append(s.paternal_id)
            if s.maternal_id != UNKNOWN:
                try:
                    s.mom = by_id[s.maternal_id]
                    s.mom.kids.append(s)
                except KeyError:
                    s.mom = None
                    self.unknown_samples.append(s.maternal_id)

    @property
    def affecteds(self):
        "generate all the affecteds in a family"
        for s in self.samples:
            if s.affected:
                yield s

    @property
    def unaffecteds(self):
        "generate all the unaffecteds in a family"
        for s in self.samples:
            if s.affected is False:
                yield s

    def trios(self, affected=True):
        "generate all the trios in a family"
        for s in self.samples:
            if affected is not None:
                if affected != s.affected:
                    continue
            if s.mom and s.dad:
                yield (s, s.mom, s.dad)


class Ped(object):
    """Manipulate pedigree data

    >>> p = Ped('pedagree/tests/a.ped')
    >>> p
    Ped('pedagree/tests/a.ped')

    >>> s = next(p.samples())
    >>> s
    Sample('family_1', 'child_1', 'dad_1', 'mom_1', 'male', 'affected', ['caucasian'])
    >>> s.ethnicity
    'caucasian'

    >>> next(p.samples(phenotype=PHENOTYPE.UNAFFECTED))
    Sample('family_1', 'dad_1', '-9', '-9', 'male', 'unaffected', ['caucasian'])

    >>> next(p.samples(phenotype=PHENOTYPE.UNAFFECTED, sex=SEX.FEMALE))
    Sample('family_1', 'mom_1', '-9', '-9', 'female', 'unaffected', ['caucasian'])

    >>> [x.sample_id for x in p.samples(phenotype=PHENOTYPE.AFFECTED, sex=SEX.FEMALE)]
    ['kid_4', 'kid_4.1']

    #>>> p.summary()

    """

    def __init__(self, ped):
        if isinstance(ped, basestring):
            self.filename = ped
            ped = open(ped)
        else:
            self.filename = ""
        self._parse(ped)
        self._graph = None

    def _parse(self, fh):
        header = None
        families = OrderedDict()

        for i, toks in enumerate(l.rstrip('\r\n').split() for l in fh):
            if i == 0 and toks[0][0] == "#":
                header = toks
                continue
            sample = Sample.from_row(toks, header=header)
            if not sample.family_id in families:
                families[sample.family_id] = []

            families[sample.family_id].append(sample)

        self.families = OrderedDict()

        for family_id, samples in families.items():
            self.families[family_id] = Family(samples)

    def __getitem__(self, sample_id):
        sample = [s for s in self.samples() if s.sample_id == sample_id]
        if len(sample) == 0:
            raise KeyError("%s not found" % sample_id)
        elif len(sample) > 1:
            raise Exception("multiple samples with id %s found" % sample_id)
        return sample[0]

    def samples(self, phenotype=None, sex=None, **kwargs):

        if phenotype is None:
            samps = (x for fam in self.families.values() for x in fam)
        else:
            samps = (x for fam in self.families.values() for x in fam if x.affected == phenotype)

        if sex is not None:
            samps = [x for x in samps if x.sex == sex]

        for k, v in kwargs.items():
            samps = [x for x in samps if getattr(x, k) == v]

        return iter(samps)

    def __repr__(self):
        return "%s('%s')" % (self.__class__.__name__, self.filename)


    def relation(self, sample_a, sample_b):
        a = self.get(sample_a)
        b = self.get(sample_b)
        if isinstance(a, list):
            a = a[0]
        if isinstance(b, list):
            b = b[0]

        if a is None or b is None:
            return 'unknown'

        # TODO: should we check anyway or just bail early like this
        if a.family_id != b.family_id:
            return 'unrelated'

        if set(a.kids).intersection(b.kids):
            return "mom-dad"

        if a.mom == b or b.mom == a or a.dad == b or b.dad == a:
            return 'parent-child'

        # TODO: do BFS
        if a.mom is None and a.dad is None and b.mom is None and b.dad is None:
            return 'unrelated'

        if a.mom == b.mom and a.dad == b.dad and None not in (a.mom, a.dad):
            return 'full siblings'

        if (a.mom is not None and a.mom == b.mom) or (a.dad is not None and a.dad == b.dad):
            return 'siblings'

        else:
            return 'related level 2'

    def get(self, sample_id, family_id=None):
        """
        get takes a sample id and optional family_id and returns the object(s)
        associated with it.
        """
        a = [x for x in self.samples() if x.sample_id == sample_id]
        if len(a) > 1 and family_id is None:
            print("multiple samples found in ped file for %s" % sample_id, file=sys.stderr)

        if family_id is not None:
            a = [x for x in a if x.family_id == family_id]
        if len(a) > 1:
            print("multiple samples found in ped file for %s" % sample_id, file=sys.stderr)
        elif len(a) == 0:
            print("no sample found in ped file for %s" % sample_id, file=sys.stderr)
            return None
        elif len(a) == 1:
            a = a[0]
        return a

    def _setup_graph(self):
        gr = self._graph = nx.DiGraph()
        for s in self.samples():
            if s.mom is not None:
                gr.add_edge(s.sample_id, s.mom.sample_id)
            if s.dad is not None:
                gr.add_edge(s.sample_id, s.dad.sample_id)
            #if s.dad is None and s.mom is None:
                # shoudl top-node be s.family_id?
            #    gr.add_edge(s.sample_id, None)

    def relatedness_coefficient(self, sample_a, sample_b, _empty=set([None])):
        """Coefficient of relatedness between 2 samples."""
        if sample_a == sample_b: return 1.0
        if self._graph is None:
            self._setup_graph()
        if not (sample_a in self._graph and sample_b in self._graph):
            return -1.0
        lca = lowest_common_ancestors(self._graph, [sample_a, sample_b]) - _empty
        if len(lca) == 0:
            return 0.0

        a_paths, b_paths = [], []
        for anc in lca:
            b = list(nx.all_shortest_paths(self._graph, sample_b, anc))
            if len(b) > 0 and len(b[-1]) > 0 and b[-1][0] == sample_b:
                b[-1] = b[-1][1:]
                if b[-1] == []:
                    b = b[:-1]
            if b:
                b_paths.extend(b)

            a = list(nx.all_shortest_paths(self._graph, sample_a, anc))
            if len(a) > 0 and len(a[-1]) > 0 and a[-1][0] == sample_a:
                a[-1] = a[-1][1:]
                if a[-1] == []:
                    a = a[:-1]
            if a:
                a_paths.extend(a)

        val = 0.0
        if len(a_paths):
            val += 0.5 ** sum(len(p) for p in a_paths)
        if len(b_paths):
            val += 0.5 ** sum(len(p) for p in b_paths)
        return val

    def sex_check(self, vcf_path, min_depth=6,
                  skip_missing=True,
                  plot=False,
                  cutoff=0.1,
                  pars=('X:10000-2781479', 'X:155701382-156030895')):
        """
        Check that the sex reported in the ped file matches that inferred
        using the genotypes in `vcf_path` using the ratio of HET / (HOM_REF +
        HOM_ALT)

        :param vcf str:  path to vcf
        :param min_depth int: minimum depth of variants to consider (in at least 50% of samples).
        :param skip_missing bool: don't consider samples that are not in the ped file
        :param plot bool: render a plot of the distributions by gender.
        :param pars tuple(str): pseudo autosmal regions

        :return: pandas.DataFrame
        """
        from cyvcf2 import VCF
        import numpy as np
        import pandas as pd


        vcf = VCF(vcf_path, gts012=True, lazy=False,
                  samples=[s.sample_id for s in self.samples()])

        pars = [x.split(':') for x in pars]
        pars = [(x[0], map(int, x[1].split('-'))) for x in pars]

        chrom = pars[0][0]

        hom_ref = np.zeros(len(vcf.samples), dtype=int)
        het     = np.zeros(len(vcf.samples), dtype=int)
        hom_alt = np.zeros(len(vcf.samples), dtype=int)
        skipped = 0
        for variant in vcf(chrom):
            depth_filter = variant.gt_depths >= min_depth
            gt_types = variant.gt_types
            if any(s <= variant.end and e >= variant.end for chrom, (s, e) in pars):
                skipped += 1
                continue
            hom_ref += (gt_types == 0) & depth_filter
            hom_alt += (gt_types == 2) & depth_filter
            het += (gt_types == 1) & depth_filter

        het_ratio = het.astype(float) / (hom_ref + hom_alt)
        print(skipped, file=sys.stderr)

        plot_vals = {'male': [], 'female': [], 'male_errors': [],
                'female_errors': [], 'male_samples': [], 'female_samples':[]}
        res = []
        for i, s in enumerate(vcf.samples):
            try:
                ped_sex = self[s].sex
            except KeyError:
                if skip_missing:
                    continue
                ped_sex = "NA"
            predicted_sex = SEX.MALE if het_ratio[i] < cutoff else SEX.FEMALE
            error = str(predicted_sex != ped_sex).upper()
            if ped_sex == "NA":
                error = "NA"
            else:
                plot_vals[ped_sex].append(het_ratio[i])

            plot_vals[ped_sex + '_errors'].append(error == "TRUE")
            plot_vals[ped_sex + '_samples'].append(s)
            res.append(dict(sample=s, ped_sex=ped_sex, hom_ref_count=hom_ref[i],
                       het_count=het[i], hom_alt_count=hom_alt[i],
                       het_ratio=het_ratio[i], predicted_sex=predicted_sex,
                       error=error))


        if not plot:
            return pd.DataFrame(res)

        from matplotlib import pyplot as plt
        plt.close()
        import seaborn as sns
        colors = sns.color_palette('Set1', 2)

        fcolors=[colors[1] if e else colors[0] for e in plot_vals['female_errors']]
        plt.scatter([0] * len(plot_vals['female']), plot_vals['female'],
                 c=fcolors, edgecolors=fcolors, marker='o')

        mcolors=[colors[0] if e else colors[1] for e in plot_vals['male_errors']]
        plt.scatter([1] * len(plot_vals['male']), plot_vals['male'],
                 c=mcolors, edgecolors=mcolors, marker='o')

        for i, e in enumerate(plot_vals['female_errors']):
            if not e: continue
            plt.text(0, plot_vals['female'][i], plot_vals['female_samples'][i],
                     color=colors[1], fontsize=7)

        for i, e in enumerate(plot_vals['male_errors']):
            if not e: continue
            plt.text(1, plot_vals['male'][i], plot_vals['male_samples'][i],
                     color=colors[0], fontsize=7)

        plt.xticks([0, 1], ['female', 'male'])
        plt.xlim(-0.1, 1.1)
        plt.ylim(ymin=0)
        plt.xlabel('Gender From Ped')
        plt.ylabel('HET / (HOM_REF + HOM_ALT) [higher is more likely female]')
        plt.savefig(plot)
        plt.close()
        return pd.DataFrame(res)

    def ped_check(self, vcf, plot=False):
        """
        Given the current pedigree and a VCF of genotypes, find sample-pairs where
        the relationship reported in the pedigree file do not match those inferred
        from the genotypes. Returns a dataframe containing all sample-pairs with
        columns for IBS0, IBS2, rel, IBS2*, pedigree_relatedness (relatedness
        coefficient expected)

        :param vcf str:  path to vcf
        :param clf: scikit-learn classifier
        :return: pandas.DataFrame
        """
        import cyvcf2
        import numpy as np
        import pandas as pd

        samps = list(self.samples())
        if isinstance(vcf, basestring):
            #samps = kwargs.pop("samples", None)
            vcf = cyvcf2.VCF(vcf, gts012=True)

        df = pd.DataFrame(list(vcf.site_relatedness()))
        df["pedigree_relatedness"] = np.array([self.relatedness_coefficient(a, b) for a, b in
                                            zip(df.sample_a, df.sample_b)])
        df["pedigree_parents"] = np.array([self.relation(a, b) == 'parent-child'  for a, b in
                                            zip(df.sample_a, df.sample_b)])
        df["predicted_parents"] = df['ibs0'] < 0.01
        df["parent_error"] = df['pedigree_parents'] != df['predicted_parents']
        if not plot:
            return df
        from matplotlib import pyplot as plt
        plt.close()
        import seaborn as sns

        colors = sns.color_palette('Set1', len(set(df['pedigree_relatedness'])))

        for i, rc in enumerate(set(df['pedigree_relatedness'])):
            sel = df['pedigree_relatedness'] == rc
            src = ("%.3f" % rc).rstrip('0')
            # outline parent kid relationships
            ec = ['k' if p else 'none' for p in df['pedigree_parents'][sel]]
            plt.scatter(df['rel'][sel], df['ibs0'][sel],
                    c=colors[i], linewidth=1, edgecolors=ec,
                    label="ped coef: %s" % src)
        plt.xlabel('coefficient of relatedness')
        plt.ylabel('ibs0')
        plt.legend()
        if plot is True:
            plt.show()
        else:
            plt.savefig(plot)
        plt.close()
        return df

    def summary(self):
        atrios, aquads = 0, 0
        for family in self.families:
            aff, sex, trios, quads = self.families[family].summary()
            atrios += trios
            aquads += quads
            d = locals()
            d['affected'] = aff[PHENOTYPE.AFFECTED]
            d['unaffected'] = aff[PHENOTYPE.AFFECTED]
            d['unknown'] = aff[PHENOTYPE.UNKNOWN]
            d['sex_unknown'] = sex[SEX.UNKNOWN]
            d['male'] = sex[SEX.MALE]
            d['female'] = sex[SEX.FEMALE]
            print("""\
===============================================
family: '{family}' :: {trios} trios and {quads} quads
===============================================
---------
phenotype
---------
affected: {affected}
unaffected: {unaffected}
unknown: {unknown}

---
sex
---
male: {male}
female: {female}
unknown: {sex_unknown}""".format(**d))
        print(atrios, aquads)

if __name__ == "__main__":
    import doctest
    print(doctest.testmod(verbose=0))
