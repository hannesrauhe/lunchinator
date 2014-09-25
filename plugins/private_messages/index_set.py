from bisect import bisect_left

class IndexSet(object):
    def __init__(self):
        self._start = []
        self._end = []
        
    def _findStart(self, idx):
        pos = bisect_left(self._start, idx)
        if pos >= len(self._start) or self._start[pos] > idx:
            return pos - 1
        return pos
        
    def addIndex(self, idx):
        self.addRange(idx, idx + 1)
                
    def addRange(self, start, end):
        if len(self._start) is 0:
            self._start.append(start)
            self._end.append(end)
            return
        
        sPos = self._findStart(start)
        # start >= self._start[sPos]
        if sPos >= 0 and start <= self._end[sPos]:
            # extending existing range
            self._end[sPos] = max(self._end[sPos], end)
        else:
            sPos += 1
            if sPos < len(self._start) and end > self._start[sPos]:
                # optimization: if merging with next range, don't insert first
                self._start[sPos] = min(self._start[sPos], start)
                self._end[sPos] = max(self._end[sPos], end)
            else:
                self._start.insert(sPos, start)
                self._end.insert(sPos, end)
            
        while sPos + 1 < len(self._start) and end > self._start[sPos + 1]:
            # merge with next range
            self._end[sPos] = max(end, self._end[sPos + 1])
            del self._start[sPos + 1]
            del self._end[sPos + 1]
        
    def __contains__(self, idx):
        if len(self._start) is 0:
            return False
        sPos = self._findStart(idx)
        return idx >= 0 and idx >= self._start[sPos] and idx < self._end[sPos]
    