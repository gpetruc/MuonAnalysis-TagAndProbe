import os, sys, json, tempfile
DCSJ = "/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions16/13TeV/DCSOnly/json_DCSONLY.txt"

def loadLumiByLsGlobal(csvfile):
    rmap = {}
    for line in open(csvfile):
        if line[0] == "#": continue
        if "STABLE BEAMS" in line: 
            fields = line.split(",")
            run = int(fields[0].split(":")[0])
            lumi = int(fields[1].split(":")[0])
            if run not in rmap: rmap[run] = {}
            rmap[run][lumi] = float(fields[6])
    ret = {}
    for run,lmap in rmap.iteritems():
        maxlumi = max(lmap.keys())
        ret[run] =  [ (lmap[i]/1e6 if i in lmap else 0) for i in xrange(maxlumi) ]
    return ret


def makeFilledBX(run, lumiByLs):
    if not os.path.exists("byxing-%d.csv" % run):
        dummylumis = []
        maxlumi = max(lumiByLs)
        for il,lumi in enumerate(lumiByLs):
            if lumi > 0.75 * maxlumi:
                dummylumis.append([il,il])
                if len(dummylumis) > 10: 
                    break
        tempjson = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump({str(run):dummylumis} , tempjson)
        tempjson.close()
        os.system("brilcalc lumi --xing --xingTr 0.1 -i %s -o byxing-%d.csv" % (tempjson.name, run))
        os.system("rm %s" % tempjson.name)
        print "lumi by xing:  byxing-%d.csv" % run
    ret = {}; allbx = []
    for line in open("byxing-%d.csv" % run):
        if line[0] == "#": continue
        fields = line.split(",")
        check = int(fields[0].split(":")[0])
        if check != run: raise RuntimeError, "Run doesn't match"
        if "STABLE BEAMS" not in line: raise RuntimeError, "Not stable beams?"
        byxings = fields[9].strip().replace("[","").replace("]","").strip().split()
        for i in xrange(len(byxings)/3):
            sibx,sdeliv,srec = byxings[(i*3):(i*3+3)]
            ibx  = int(byxings[i*3])
            lumi = float(byxings[i*3+1])
            if ibx not in ret: ret[ibx] = []
            ret[ibx].append(lumi)
            allbx.append(lumi)
    allbx.sort()
    cut = 0.25*allbx[((len(allbx)-1)*3)/4]
    bxs = [ 0 for x in xrange(3563) ]
    for ibx,hits in ret.iteritems():
        hits.sort(reverse=True)
        if hits[len(hits)/2] > cut:
            bxs[ibx]=1
    cbunches = sum(bxs)
    dump = open("bxs-%d-%db.txt" % (run,cbunches), "w")
    dump.write( "|" + "".join("%-10s"  % ((i/100)%10)  for i in xrange(356)) + " \n")
    dump.write( "|" + "".join("%-10s"  % ((i/10)%10)   for i in xrange(356)) + " \n")
    dump.write( "|" + "".join("%-10s"  % (i%10)        for i in xrange(356)) + " \n")
    dump.write( "|" + "".join("0123456789" for i in xrange(356)) + " \n")
    dump.write( "|" + "".join(("X" if i else " ") for i in bxs) + "|\n")
    return bxs

if __name__ == "__main__":
    for csvfile in sys.argv[1:]:
        rmap = loadLumiByLsGlobal(csvfile)
        for run, byls in sorted(rmap.iteritems()):
            print "%d  %.1f pb" % (run, sum(byls))
            if sum(byls) > 1:
                makeFilledBX(run, byls)
    


