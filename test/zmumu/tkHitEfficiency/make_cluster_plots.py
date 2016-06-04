from glob import glob
from array import array
import os, ROOT, sys

c1 = None
SAFE_COLOR_LIST=[ ROOT.kBlack, ROOT.kRed, ROOT.kGreen+2, ROOT.kBlue, ROOT.kMagenta+1, ROOT.kOrange+7, ROOT.kCyan+1, ROOT.kGray+2, ROOT.kViolet+5, ROOT.kSpring+5, ROOT.kAzure+1, ROOT.kPink+7, ROOT.kOrange+3, ROOT.kBlue+3, ROOT.kMagenta+3, ROOT.kRed+2, ]

lumiAndRun = [
  ( 7, [274314] ),
  ( 6.5, [274315,274316] ),
  ( 6, [274284] ),
  ( 4, [274157,274200] ),
  ( 3, [273554,273555] ),
  ( 2, [273502,273503] ),
  ( 1.5, [273158] ),
  ( 1.0, [273013,273017] ),
  ( 0.8, [272936] ),
  ( 0.2, [272798] ),
]
fillingAndRun = [
   ( 74, [ 272798,  ] ),
   ( 301, [ 272811, 272812, 272818, 272930, 272936, 273013, 273017,  ] ),
   ( 589, [ 273158, 273291, 273299, 273301, 273302, 273402, 273403, 273406, 273409, 273410, 273425, 273426, 274094,  ] ),
   ( 877, [ 273446, 273447, 273448, 273449, 273450, 273492, 273493, 273494, 273502, 273503,  ] ),
   ( 1165, [ 273554, 273555, 273725, 273728, 273730, 274146,  ] ),
   ( 1453, [ 274157, 274159, 274160, 274161,  ] ),
   ( 1740, [ 274172, 274198, 274199, 274200, 274240, 274241, 274244,  ] ),
   ( 1812, [ 274250, 274251, 274284, 274286,  ] ),
   ( 2028, [ 274314, 274315, 274316, 274319,  ] ),
]
runs = sum([r for (l,r) in lumiAndRun], [] )

layersForEff = [ (0,'TIB',4), (4,'TOB',6), (10,'TID',3), (13,'TEC',9) ]

_lumiProvider = None
def initLumiProvider():
    global _lumiProvider;
    if _lumiProvider == None:
        ROOT.gROOT.ProcessLine(".L /afs/cern.ch/work/g/gpetrucc/TnP/CMSSW_8_0_8/src/MuonAnalysis/TagAndProbe/test/zmumu/lumiTools.cc+")
        _lumiProvider = True

def loadLumiByLs(run):
    initLumiProvider()
    ret = {}
    for line in open("byls-%d.csv" % run):
        if line[0] == "#": continue
        fields = line.split(",")
        check = int(fields[0].split(":")[0])
        if check != run: raise RuntimeError, "Run doesn't match"
        if "STABLE BEAMS" in line: 
            lumi = int(fields[1].split(":")[0])
            ret[lumi] = float(fields[6])
    maxlumi = max(ret.keys())
    ROOT.setLumiByLs(run, maxlumi, array('f', [ (ret[i]/23e3 if i in ret else 0) for i in xrange(maxlumi) ] ))

def loadLumiByLsGlobal():
    initLumiProvider()
    rmap = {}
    for line in open("byls-all.csv"):
        if line[0] == "#": continue
        if "STABLE BEAMS" in line: 
            fields = line.split(",")
            run = int(fields[0].split(":")[0])
            lumi = int(fields[1].split(":")[0])
            if run not in rmap: rmap[run] = {}
            rmap[run][lumi] = float(fields[6])
    for run,lmap in rmap.iteritems():
        maxlumi = max(lmap.keys())
        ROOT.setLumiByLs(run, maxlumi, array('f', [ (lmap[i]/23e3 if i in lmap else 0) for i in xrange(maxlumi) ] ))

def chainForRun(runs):
    chain = ROOT.TChain("tpTree/fitter_tree");
    if runs == "MC":
        chain.Add("tnpZ_MC.root")
        return chain
    for run in runs:
        for f in glob("tnpZ_Data_Express_run%d*.root" % run):
            if os.stat(f).st_size > 1000:
                chain.Add(f)
    return chain

def chainGlobal():
    chain = ROOT.TChain("tpTree/fitter_tree");
    for f in glob("tnpZ_hitEff_Data_v*.root"):
        if os.stat(f).st_size > 1000:
            chain.Add(f)
    return chain


def cpeff(passing,failing):
    passing = int(passing)
    total   = int(passing + failing)
    cpcalc = ROOT.TEfficiency.ClopperPearson
    if total:
         y0 = passing/float(total)
         ymax = cpcalc(total,passing,0.6827,True )
         ymin = cpcalc(total,passing,0.6827,False)
         return (y0, ymin-y0, ymax-y0)
    else:
        return None

def makeEff(num, den, xexpr, xbins, chain, prune = lambda effs : True):
    nsel = chain.Draw("%s:%s >> htemp(%s,2,-0.5,1.5)" % (num, xexpr, xbins), den, "GOFF")
    if nsel == 0: return None
    htemp = ROOT.gROOT.FindObject("htemp")
    if not htemp: return None
    points  = []
    for ix in xrange(1,htemp.GetNbinsX()+1):
        x  = htemp.GetXaxis().GetBinCenter(ix)
        xl = htemp.GetXaxis().GetBinLowEdge(ix)
        xh = htemp.GetXaxis().GetBinUpEdge(ix)
        nfail = htemp.GetBinContent(ix,1)
        npass = htemp.GetBinContent(ix,2)
        if npass + nfail == 0: continue
        effs = cpeff(npass,nfail)
        if not prune(effs): continue
        points.append( (x, effs[0], x-xl, xh-x, -effs[1], effs[2]) ) 
    ret = ROOT.TGraphAsymmErrors(len(points))
    for i,(x,y,dx1,dx2,dy1,dy2) in enumerate(points):
        ret.SetPoint(i, x, y)
        ret.SetPointError(i, dx1, dx2, dy1, dy2)
    return ret

def makeHist(den, xexpr, xbins, chain, _iplot=[0]):
    chain.Draw("%s >> htemp(%s)" % (xexpr, xbins), den, "GOFF")
    htemp = ROOT.gROOT.FindObject("htemp")
    if not htemp: raise RuntimeError
    htemp = htemp.Clone("tmp%d" % _iplot[0]); 
    htemp.SetDirectory(None)
    htemp.SetBinContent(1, htemp.GetBinContent(0)+htemp.GetBinContent(1))
    nb = htemp.GetNbinsX()
    htemp.SetBinContent(nb, htemp.GetBinContent(nb+1)+htemp.GetBinContent(nb))
    _iplot[0] += 1
    return htemp


def makeEffVsBX(num, den, chain):
    return makeEff(num, den, "tag_bx", "20,0,4000", chain)
def makeEffVsBXfine(num, den, chain):
    return makeEff(num, den, "tag_bx", "501,-0.5,4000.5", chain)
def makeEffVsPU(num, den, chain):
    return makeEff(num, den, "tag_nVertices", "15,0,45", chain)
def makeEffVsLS(num, den, chain):
    return makeEff(num, den, "lumi", "20,0,4000", chain)

def frameMR():
    nbins = layersForEff[-1][0]+layersForEff[-1][2]
    frame = ROOT.TH1D("frameMR","frameMR",nbins,0,nbins)
    for O,S,L in layersForEff:
        for iL in xrange(1,L+1):
            frame.GetXaxis().SetBinLabel(iL+O, "%s%d" % (S,iL))
    frame.GetYaxis().SetRangeUser(0,1)
    frame.GetXaxis().LabelsOption("V")
    return frame

def mergePoints(graphs):
    ret = ROOT.TGraphAsymmErrors(sum(g.GetN() for g in graphs))
    ipoint = 0
    for g in graphs:
        for isrc in xrange(g.GetN()):
            ret.SetPoint(ipoint, g.GetX()[isrc], g.GetY()[isrc])
            ret.SetPointError(ipoint, g.GetErrorXlow(isrc), g.GetErrorXhigh(isrc), g.GetErrorYlow(isrc), g.GetErrorYhigh(isrc))
            ipoint += 1
    return ret

def makeEffsMR(dendef, den, chain):
    rets = []
    for O,S,L in layersForEff:
        for iL in xrange(1,L+1):
            rets.append(makeEff("tk%s%sHitEff%s" % (S,iL,"Num"), "tk%s%sHitEff%s && %s" % (S,iL,dendef, den), str(O+iL-0.5), "1,%d,%d" % (O+iL-1,O+iL), chain))
    return mergePoints(rets)    

def doLegend(plots, corner='TL', textSize=0.035, legWidth=0.18):
    nentries = len(plots)
    if corner == "TR":
        (x1,y1,x2,y2) = (.90-legWidth, .75 - textSize*max(nentries-3,0), .90, .93)
    elif corner == "TC":
        (x1,y1,x2,y2) = (.5, .75 - textSize*max(nentries-3,0), .5+legWidth, .93)
    elif corner == "TL":
        (x1,y1,x2,y2) = (.2, .75 - textSize*max(nentries-3,0), .2+legWidth, .93)
    elif corner == "BR":
        (x1,y1,x2,y2) = (.90-legWidth, .33 + textSize*max(nentries-3,0), .90, .15)
    elif corner == "BC":
        (x1,y1,x2,y2) = (.5, .33 + textSize*max(nentries-3,0), .5+legWidth, .15)
    elif corner == "BL":
        (x1,y1,x2,y2) = (.2, .33 + textSize*max(nentries-3,0), .2+legWidth, .15)
    leg = ROOT.TLegend(x1,y1,x2,y2)
    leg.SetFillColor(0)
    leg.SetShadowColor(0)
    #leg.SetLineColor(0)
    leg.SetTextFont(42)
    leg.SetTextSize(textSize)
    for k,v in plots:
        leg.AddEntry(v, k, 'LPE')
    return leg

def stackPlots(out, maybeplots, frame=None, legend='BR', ymin=0, hlines=[]):
    plots = [ (k,p) for (k,p) in maybeplots if p ]
    if not plots: 
        print "No valid plots for %s" % out
        return
    c1.Clear(); c1.SetGridy(True)
    for i,(key, p) in enumerate(plots):
        p.SetMarkerColor(SAFE_COLOR_LIST[i])
        p.SetLineColor(SAFE_COLOR_LIST[i])
        p.SetLineWidth(2)
    if not frame:
        xmax = max([ max([ p.GetX()[i]+p.GetErrorXhigh(i) for i in xrange(p.GetN()) ]) for (k,p) in plots ])
        xmin = min([ min([ p.GetX()[i]+p.GetErrorXlow(i) for i in xrange(p.GetN()) ]) for (k,p) in plots ])
        frame = ROOT.TH1D("frame","frame",100,xmin,xmax)
    frame.Draw()
    frame.GetYaxis().SetRangeUser(ymin,1)
    if hlines:
        line = ROOT.TLine()
        for i,y in enumerate(hlines):
            line.SetLineWidth(2); line.SetLineStyle(7);
            line.SetLineColor(SAFE_COLOR_LIST[i])
            line.DrawLine(xmin,y,xmax,y)
    for (key,p) in plots: p.Draw("PZ SAME")
    if len(plots) > 1:
        leg = doLegend(plots, corner=legend); leg.Draw()
    c1.Print("plots/"+out+".png")
    c1.Print("plots/"+out+".pdf")
    fOUT = ROOT.TFile.Open("plots/"+out+".root","RECREATE")
    if frame: fOUT.WriteTObject(frame, "frame");
    for (key,p) in plots: fOUT.WriteTObject(p, key)
    fOUT.Close()

def stackHists(out, plots, legend='TL', ymin=0):
    c1.Clear(); c1.SetGridy(False)
    stk = ROOT.THStack("stk","stk")
    for i,(key, p) in enumerate(plots):
        if p.Integral() == 0: continue
        p.Scale(1.0/p.Integral())
        p.SetLineColor(SAFE_COLOR_LIST[i])
        p.SetLineWidth(2)
        p.GetXaxis().SetNdivisions(505)
        stk.Add(p)
    stk.Draw("HIST NOSTACK")
    stk.GetXaxis().SetNdivisions(505)
    if len(plots) > 1:
        leg = doLegend(plots, corner=legend); leg.Draw()
    c1.Print("plots/"+out+".png")
    c1.Print("plots/"+out+".pdf")

def suite(name,cut,labelsAndRuns):
    labels = [ l for (l,r) in labelsAndRuns ]
    runs   = [ r for (l,r) in labelsAndRuns ]
    chains = map(chainForRun,runs)
    dosuite(name, labels, chains, [cut for l in labels])

def suiteByCut(name,chain,labelsAndCuts):
    labels = [ l for (l,c) in labelsAndCuts ]
    cuts   = [ c for (l,c) in labelsAndCuts ]
    dosuite(name, labels, [ chain for c in cuts ], cuts)

def dosuite(name,labels, chains, cuts):
    os.system("mkdir -p plots/"+name)
    os.system("cp /afs/cern.ch/user/g/gpetrucc/php/index.php plots/"+name+"/")
    for dendef in "Den1","Den0":
        for O,S,L in layersForEff:
            for iL in xrange(1,L+1):
                lname = "%s%d" % (S,iL)
                num   = "tk%sHitEffNum" % lname
                den   = "tk%sHitEff%s"  % (lname,dendef)
                effs = [ (l,makeEffVsBXfine(num,den+"&&"+cut,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
                stackPlots(name+"/eff_%s_%s_bx" % (lname,dendef), effs, ymin=0.5)
                continue
                effs = [ (l,makeEffVsBX(num,den+"&&"+cut,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
                stackPlots(name+"/eff_%s_%s_bx" % (lname,dendef), effs, ymin=0.5)
                effs = [ (l,makeEffVsPU(num,den+"&&"+cut,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
                stackPlots(name+"/eff_%s_%s_nvtx" % (lname,dendef), effs, ymin=0.5)
                effs = [ (l,makeEffVsLS(num,den+"&&"+cut,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
                stackPlots(name+"/eff_%s_%s_ls" % (lname,dendef), effs, ymin=0.5)
        continue
        frame = frameMR()
        effs = [ (l,makeEffsMR(dendef,cut,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
        stackPlots(name+"/eff_summary_%s" % dendef, effs, frame=frame, ymin=0.7)
    for xn,xvar,xbins in ("eta","eta","25,-2.5,2.5"), ("nvtx","tag_nVertices","5,5,30"):
        break
        effs = [ (l,makeEff("TK_classic",cut,xvar,xbins,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
        stackPlots(name+"/eff_TK_classic_"+xn, effs, ymin=0.7)
        effs = [ (l,makeEff("TK_earlyGeneral",cut,xvar,xbins,c)) for (l,c,cut) in zip(labels,chains,cuts) ]
        stackPlots(name+"/eff_TK_earlyGeneral_"+xn, effs, ymin=0.7)
    for vname, var, xbins in [ 
            #('validHits', 'tkValidHits', '30,0.5,30.5'),
            #('validStripHits', 'tkValidStripHits', '26,-0.5,25.5'),
            #('lostStripHits',  'tkLostStripHits',  '5,-0.5,4.5'),
            #('trackerLayers', 'tkTrackerLay', '15,0.5,15.5'),
            #('expIn', 'tkExpHitIn', '7,-0.5,6.5'),
            #('expOut', 'tkExpHitOut', '10,-0.5,9.5'),
            #('validFraction', 'tkHitFract', '25,0.75,1.0'),
            ('charge0', 'clusterCharge0', '50,0,5000'),
            ('charge1', 'clusterCharge1', '50,0,5000'),
            ('charge2', 'clusterCharge2', '50,0,5000'),
            ('charge3', 'clusterCharge3', '50,0,5000'),
            ('charge4', 'clusterCharge4', '50,0,5000'),
            ('chargeM', 'clusterChargeM', '65,0,6500')
            ]:
        break
        if "Lost" in var or "ExpHit" in var:
            legend = 'TR'; c1.SetLogy(True)
        else:
            legend = 'TL'; c1.SetLogy(False)
        hists = [ (l,makeHist(cut, var, xbins, c)) for (l,c,cut) in zip(labels,chains,cuts) ]
        stackHists( name+"/hist_"+vname, hists, legend=legend )
    for O,S,L in layersForEff:
        break
        for iL in xrange(1,L+1):
            lname = "%s%d" % (S,iL)
            for vname, var, xbins in [ 
                            ('charge%sMin'%lname, 'clusterChargeMin%s'%lname, '75,0,7500'),
                            ('charge%sMax'%lname, 'clusterChargeMax%s'%lname, '75,0,7500') ]:
                hists = [ (l,makeHist(cut+"&& clusterChargeMax%s < 99999" % lname, var, xbins, c, cut)) for (l,c,cut) in zip(labels,chains,cuts) ]
                stackHists( name+"/hist_"+vname, hists, legend="TR" )

def lumiSuiteOld(name,cut):
    lumis = [ l for (l,r) in lumiAndRun ]
    runs  = [ r for (l,r) in lumiAndRun ]
    chains = map(chainForRun,runs)
    for dendef in "Den1","Den0":
        for O,S,L in layersForEff:
            effs = []
            for iL in xrange(1,L+1):
                lname = "%s%d" % (S,iL)
                num   = "tk%sHitEffNum" % lname
                den   = "tk%sHitEff%s && %s"  % (lname,dendef,cut)
                graphs = [ makeEff(num,den, str(l), "1,%g,%g"%(l*0.9,l*1.1), c)  for (l,c) in zip(lumis,chains) ]
                effs.append( (lname, mergePoints(graphs)) )
            stackPlots(name+"/eff_%s_%s_lumi" % (S,dendef), effs, ymin=0.75, legend="BL")

def lumiSuiteNew(name,cut):
    for r in runs: loadLumiByLs(r)
    chain = chainForRun(runs)
    mcch  = chainForRun("MC")
    for dendef in "Den1","Den0":
        for O,S,L in layersForEff:
            effs = []; hlines = []
            for iL in xrange(1,L+1):
                lname = "%s%d" % (S,iL)
                num   = "tk%sHitEffNum" % lname
                den   = "tk%sHitEff%s && %s"  % (lname,dendef,cut)
                graph =  makeEff(num,den, 'lumiByLs(run,lumi)',  '100,0.0,10.0', chain, prune = lambda effs : max(abs(effs[1]),abs(effs[2])) < 0.01)
                mceff  = makeEff(num,den, '5', '1,0.0,10.0', mcch)
                effs.append( (lname, graph) )
                hlines.append( mceff.GetY()[0] )
            stackPlots(name+"/eff_%s_%s_lumiE33" % (S,dendef), effs, ymin=0.75, legend="BL", hlines = hlines)

def lumiSuiteGlobal(name,cut):
    loadLumiByLsGlobal()
    chain = chainGlobal()
    for dendef in "Den1","Den0":
        for O,S,L in layersForEff:
            effs = []
            for iL in xrange(1,L+1):
                lname = "%s%d" % (S,iL)
                num   = "tk%sHitEffNum" % lname
                den   = "tk%sHitEff%s && %s && lumiByLs(run,lumi) > 0"  % (lname,dendef,cut)
                graph =  makeEff(num,den, 'lumiByLs(run,lumi)', '100,0.0,10.0', chain, prune = lambda effs : max(abs(effs[1]),abs(effs[2])) < 0.01)
                effs.append( (lname, graph) )
            stackPlots(name+"/eff_%s_%s_lumiE33_promptReco" % (S,dendef), effs, ymin=0.75, legend="BL")
 
        
def lumiTest(name,cut,labelAndRun):
    labels = [ l for (l,r) in labelAndRun ]
    runs  = [ r for (l,r) in labelAndRun ]
    chains = map(chainForRun,runs)
    for rs in runs: loadLumiByLs(rs[0])
    hists = [ (l,makeHist(cut, 'lumiByLs(run,lumi)', '60,0.0,10.0', c)) for (l,c) in zip(labels,chains) ]
    stackHists( name+"/hist_lumiByLsE33", hists, legend='TR')

if __name__ == "__main__":
    ROOT.gROOT.SetBatch(True)
    ROOT.gROOT.ProcessLine(".x /afs/cern.ch/user/g/gpetrucc/cpp/tdrstyle.cc")
    ROOT.gStyle.SetOptStat(0)
    ROOT.gStyle.SetOptTitle(0)
    c1 = ROOT.TCanvas("c1","c1",800,800)
    #labelsAndRuns = [("run%s" % r, [r]) for r in runs]
    #lumiTest("testLumi","tag_IsoMu20",labelsAndRuns)
    if sys.argv[1] == "suite":
        labelsAndRuns = [ ("MC","MC") ] + [("lumi%s" % l, rs) for (l,rs) in lumiAndRun]
        suite("testLumi","tag_IsoMu20", labelsAndRuns)
    if sys.argv[1] == "filling":
        labelsAndRuns = [ ("%d b" % b, rs) for (b,rs) in fillingAndRun ]
        suite("testLumiBxFine","tag_IsoMu20", labelsAndRuns)
    if sys.argv[1] == "filling-prompt":
        chain = chainGlobal()
        labelsAndCuts = [ ("%d b" % b, "tag_IsoMu20 && ("+("||".join(["run==%d"%r for r in rs]))+")") for (b,rs) in fillingAndRun  ]
        print labelsAndCuts
        suiteByCut("testLumiBxFine", chain, labelsAndCuts ) #[ ("all", "tag_IsoMu20") ] )
    if sys.argv[1] == "lumi":
        lumiSuiteNew("testLumi","tag_IsoMu20")
    if sys.argv[1] == "prompt":
        lumiSuiteGlobal("testLumiPromptReco","tag_IsoMu20 && tag_nVertices > 0")
