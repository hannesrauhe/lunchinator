from private_messages.index_set import IndexSet
from random import randint

if __name__ == '__main__':
    s = IndexSet()
    s.addRange(3, 4)
    assert 2 not in s
    assert 3 in s
    assert 4 not in s
    
    s.addRange(4, 6)
    assert 4 in s
    assert 5 in s
    assert 6 not in s
    
    s = IndexSet()
    s.addRange(3, 6)
    s.addRange(4, 7)
    assert 2 not in s
    assert 3 in s
    assert 4 in s
    assert 5 in s
    assert 6 in s
    assert 7 not in s
    
    s = IndexSet()
    s.addRange(2, 4)
    s.addRange(1, 3)
    assert 0 not in s
    assert 1 in s
    assert 2 in s
    assert 3 in s
    assert 4 not in s
    
    s = IndexSet()
    s.addRange(1, 5)
    s.addRange(2, 4)
    assert 0 not in s
    assert 1 in s
    assert 2 in s
    assert 3 in s
    assert 4 in s
    assert 5 not in s
    
    repetitions = 100
    numRanges = 5
    minIdx = 0
    maxIdx = 100
    for _ in xrange(repetitions):
        s = IndexSet()
        sTest = set()
        for __ in xrange(numRanges): 
            start = randint(minIdx, maxIdx)
            end = randint(minIdx, maxIdx)
            if start == end:
                continue
            if start > end:
                start, end = end, start
            s.addRange(start, end)
            for idx in xrange(start, end):
                sTest.add(idx)
            
            for possIdx in xrange(minIdx, maxIdx):
                if possIdx in sTest:
                    assert possIdx in s
                else:
                    assert possIdx not in s
    print "All tests succeeded."