from peddy import Ped, Family, Sample, PHENOTYPE, SEX

def test_sample():
    s = Sample('fam1', 'sample1', '-9', '-9', '2', '2')

    assert s.sex == SEX.FEMALE, (s.sex)
    assert s.affected == PHENOTYPE.AFFECTED
    assert s.kids == []

def test_sample_str_and_from_row():
    s = Sample('fam1', 'sample1', '-9', '-9', '2', '2')
    assert str(s) == "fam1 sample1 -9 -9 2 2", str(s)

    s2 = Sample.from_row(str(s))
    assert s2.sample_id == s.sample_id
    assert s2.sex == s.sex
    assert s2.family_id == s.family_id



def test_family():
    kid = Sample('fam1', 'kid', 'dad', 'mom', '2', '2')
    mom = Sample('fam1', 'mom', '-9', '-9', '2', '2')
    dad = Sample('fam1', 'dad', '-9', '-9', '1', '2')

    f = Family([kid, mom, dad])

    assert mom.kids == [kid]
    assert dad.kids == [kid]

    assert kid.dad == dad
    assert kid.mom == mom

    assert list(f.affecteds) == [kid, mom, dad], list(f.affecteds)
    assert list(f.unaffecteds) == []

    assert list(f) == [kid, mom, dad]


def test_ped():

    p = Ped('peddy/tests/a.ped')
    assert len(p.families) == 4

    assert len(list(p.samples())) == 12
