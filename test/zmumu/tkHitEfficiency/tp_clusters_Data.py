import FWCore.ParameterSet.Config as cms

process = cms.Process("TagProbe")

process.load('Configuration.StandardSequences.Services_cff')
process.load('FWCore.MessageService.MessageLogger_cfi')
process.options   = cms.untracked.PSet( wantSummary = cms.untracked.bool(True) )
process.MessageLogger.cerr.FwkReport.reportEvery = 100
process.MessageLogger.suppressError = cms.untracked.vstring("patTriggerFull")
process.source = cms.Source("PoolSource", 
    #fileNames = cms.untracked.vstring('/store/data/Run2015D/SingleMuon/RAW-RECO/ZMu-PromptReco-v4/000/258/425/00000/361B6FC1-236E-E511-B4F1-02163E014366.root'),
    fileNames = cms.untracked.vstring('/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/04312D9B-C027-E611-8E01-02163E0135AA.root')
    #lumisToProcess = cms.untracked.VLuminosityBlockRange()
)
JSON = '/afs/cern.ch/cms/CAF/CMSCOMM/COMM_DQM/certification/Collisions16/13TeV/DCSOnly/json_DCSONLY.txt'
import FWCore.PythonUtilities.LumiList as LumiList
process.source.lumisToProcess = LumiList.LumiList(filename = JSON).getVLuminosityBlockRange()

process.maxEvents = cms.untracked.PSet( input = cms.untracked.int32(-1) )    

process.load('Configuration.StandardSequences.GeometryRecoDB_cff')
process.load('Configuration.StandardSequences.MagneticField_cff')
process.load('Configuration.StandardSequences.FrontierConditions_GlobalTag_condDBv2_cff')
process.load("Configuration.StandardSequences.Reconstruction_cff")

from Configuration.AlCa.GlobalTag import GlobalTag
process.GlobalTag = GlobalTag(process.GlobalTag, '80X_dataRun2_Express_v6', '')

#process.load("HLTrigger.HLTfilters.triggerResultsFilter_cfi")
process.triggerResultsFilter = cms.EDFilter("TriggerResultsFilter",
    daqPartitions = cms.uint32(1),
    hltResults = cms.InputTag("TriggerResults","","HLT"),
    l1tIgnoreMask = cms.bool(False),
    l1tResults = cms.InputTag(""),
    l1techIgnorePrescales = cms.bool(False),
    throw = cms.bool(True),
    triggerConditions = cms.vstring('HLT_IsoMu20_v*')
)

process.preselMu = cms.EDFilter("MuonSelector",
    src = cms.InputTag("muons"),
    cut = cms.string("track.isNonnull && pt > 10"),
    filter = cms.bool(True)
)
process.preselPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 140'),
    decay = cms.string('preselMu@+ preselMu@-')
)
process.onePreselPair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("preselPairs"), minNumber = cms.uint32(1))
process.preselSeq = cms.Sequence(process.preselMu + process.preselPairs + process.onePreselPair)

process.load("MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff")
process.muonMatchHLTL3.maxDeltaR = 0.1
from MuonAnalysis.MuonAssociators.patMuonsWithTrigger_cff import *

from MuonAnalysis.TagAndProbe.common_variables_cff import *
process.load("MuonAnalysis.TagAndProbe.common_modules_cff")

process.tagMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 20 && numberOfMatchedStations >= 2"+
                     " && !triggerObjectMatchesByCollection('hltL3MuonCandidates').empty()"+
                     " && pfIsolationR04().sumChargedHadronPt/pt < 0.2"),
)
process.oneTag  = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tagMuons"), minNumber = cms.uint32(1))

process.probeMuons = cms.EDFilter("PATMuonSelector",
    src = cms.InputTag("patMuonsWithTrigger"),
    cut = cms.string("pt > 10 && numberOfMatchedStations >= 1 && innerTrack.isNonnull"), 
)
process.clusterInfo = cms.EDProducer("ClusterShapeFilterStudies",
        probes = cms.InputTag("probeMuons"),
        estimateCut = cms.double(10), 
        # configuraton for refitter
        DoPredictionsOnly = cms.bool(False),
        Fitter = cms.string('KFFitterForRefitInsideOut'),
        TrackerRecHitBuilder = cms.string('WithAngleAndTemplate'),
        Smoother = cms.string('KFSmootherForRefitInsideOut'),
        MuonRecHitBuilder = cms.string('MuonRecHitBuilder'),
        RefitDirection = cms.string('alongMomentum'),
        RefitRPCHits = cms.bool(True),
        Propagator = cms.string('SmartPropagatorAnyRKOpposite'),
)

process.tpPairs = cms.EDProducer("CandViewShallowCloneCombiner",
    cut = cms.string('60 < mass < 140'),
    decay = cms.string('tagMuons@+ probeMuons@-')
)
process.onePair = cms.EDFilter("CandViewCountFilter", src = cms.InputTag("tpPairs"), minNumber = cms.uint32(1))

from MuonAnalysis.TagAndProbe.muon.tag_probe_muon_extraIso_cff import ExtraIsolationVariables

process.tpTree = cms.EDAnalyzer("TagProbeFitTreeProducer",
    tagProbePairs = cms.InputTag("tpPairs"),
    arbitration   = cms.string("OneProbe"),
    variables = cms.PSet(
        AllVariables,
        clusterChargeM = cms.InputTag("clusterInfo", "median"),
        clusterCharge0 = cms.InputTag("clusterInfo", "byCharge0"),
        clusterCharge1 = cms.InputTag("clusterInfo", "byCharge1"),
        clusterCharge2 = cms.InputTag("clusterInfo", "byCharge2"),
        clusterCharge3 = cms.InputTag("clusterInfo", "byCharge3"),
        clusterCharge4 = cms.InputTag("clusterInfo", "byCharge4"),
        tkValidStripHits = cms.string("track.hitPattern.numberOfValidStripHits"),
        tkLostStripHits = cms.string("track.hitPattern.numberOfLostStripHits('TRACK_HITS')"),
        tkValidStripTIBHits = cms.string("track.hitPattern.numberOfValidStripTIBHits"),
        tkLostStripTIBHits = cms.string("track.hitPattern.numberOfLostStripTIBHits('TRACK_HITS')"),
        tkValidStripTIDHits = cms.string("track.hitPattern.numberOfValidStripTIDHits"),
        tkLostStripTIDHits = cms.string("track.hitPattern.numberOfLostStripTIDHits('TRACK_HITS')"),
        tkValidStripTOBHits = cms.string("track.hitPattern.numberOfValidStripTOBHits"),
        tkLostStripTOBHits = cms.string("track.hitPattern.numberOfLostStripTOBHits('TRACK_HITS')"),
        tkValidStripTECHits = cms.string("track.hitPattern.numberOfValidStripTECHits"),
        tkLostStripTECHits = cms.string("track.hitPattern.numberOfLostStripTECHits('TRACK_HITS')"),
    ),
    flags = cms.PSet(
       TrackQualityFlags,
       MuonIDFlags,
       HighPtTriggerFlags,
       HighPtTriggerFlagsDebug,
    ),
    tagVariables = cms.PSet(
        AllVariables,
        nVertices   = cms.InputTag("nverticesModule"),
        bx     = cms.InputTag("l1rate","bx"),
    ),
    tagFlags = cms.PSet(HighPtTriggerFlags,HighPtTriggerFlagsDebug),
    pairVariables = cms.PSet(
        dz      = cms.string("daughter(0).vz - daughter(1).vz"),
        pt      = cms.string("pt"), 
    ),
    pairFlags = cms.PSet(
    ),
    isMC           = cms.bool(False),
    addRunLumiInfo = cms.bool(True),
)
STEPS = [ 'initialStep', 'lowPtTripletStep', 'pixelPairStep', 'detachedTripletStep', 'mixedTripletStep', 'pixelLessStep', 'tobTecStep', 'jetCoreRegionalStep', 'muonSeededStepInOut', 'muonSeededStepOutIn' ]
for S in STEPS:
    setattr(process.tpTree.flags, 'TK_'+S, cms.string('innerTrack.isAlgoInMask("%s")' % S))
setattr(process.tpTree.flags, 'TK_classic',      cms.string("||".join('innerTrack.isAlgoInMask("%s")' % S for S in STEPS if "muon" not in S and "jetCore" not in S)))
setattr(process.tpTree.flags, 'TK_earlyGeneral', cms.string("||".join('innerTrack.isAlgoInMask("%s")' % S for S in STEPS if "muon" not in S)))
for ID,S,L in (3,'TIB',4), (4,'TID',3), (5,'TOB',6), (6,'TEC',9):
    for iL in xrange(1,L+1):
        setattr(process.tpTree.variables, 'tk%s%dLayerCaseTK' % (S,iL), cms.string("track.hitPattern.getTrackerLayerCase('TRACK_HITS',         %d, %d)" % (ID,iL)))
        setattr(process.tpTree.variables, 'tk%s%dLayerCaseEI' % (S,iL), cms.string("track.hitPattern.getTrackerLayerCase('MISSING_INNER_HITS', %d, %d)" % (ID,iL)))
        setattr(process.tpTree.variables, 'tk%s%dLayerCaseEO' % (S,iL), cms.string("track.hitPattern.getTrackerLayerCase('MISSING_OUTER_HITS', %d, %d)" % (ID,iL)))
        setattr(process.tpTree.flags, 'tk%s%dHitEffNum' % (S,iL), 
                cms.string(          "track.hitPattern.getTrackerLayerCase('TRACK_HITS', %d, %d) == 0" % (ID,iL)))
        setattr(process.tpTree.flags, 'tk%s%dHitEffDen0' % (S,iL), 
                cms.string(          "track.hitPattern.getTrackerLayerCase('TRACK_HITS', %d, %d) <= 1" % (ID,iL)))
        setattr(process.tpTree.flags, 'tk%s%dHitEffDen1' % (S,iL), 
                cms.string("||".join("track.hitPattern.getTrackerLayerCase('%s', %d, %d) <= 1" % (T,ID,iL) for T in 'TRACK_HITS MISSING_INNER_HITS MISSING_OUTER_HITS'.split())))
        setattr(process.tpTree.flags, 'tk%s%dHitEffDen2' % (S,iL), 
                cms.string("||".join("track.hitPattern.getTrackerLayerCase('%s', %d, %d) <= 3" % (T,ID,iL) for T in 'TRACK_HITS MISSING_INNER_HITS MISSING_OUTER_HITS'.split())))
        setattr(process.tpTree.variables, 'clusterChargeMin%s%d' % (S,iL), cms.InputTag("clusterInfo","byLayerMin%s%d" %(S,iL)))
        setattr(process.tpTree.variables, 'clusterChargeMax%s%d' % (S,iL), cms.InputTag("clusterInfo","byLayerMax%s%d" %(S,iL)))
    

process.tagAndProbe = cms.Path( 
    process.triggerResultsFilter +
    process.preselSeq  +
    process.patMuonsWithTriggerSequence +
    process.tagMuons +
    process.oneTag     +
    process.probeMuons +
    process.tpPairs    +
    process.onePair    +
    process.clusterInfo +
    #process.clusterInfoT +
    process.nverticesModule +
    process.l1rate +
    process.tpTree
)

process.TFileService = cms.Service("TFileService", fileName = cms.string("tnpZ_Data_Express.root"))
process.source.fileNames = [
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/02EC4195-BC27-E611-8F8A-02163E014428.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/04312D9B-C027-E611-8E01-02163E0135AA.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/060D6F42-B827-E611-B680-02163E011D8D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/06853318-BA27-E611-899F-02163E0141AC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/0A289513-C027-E611-8F69-02163E012807.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/0A4ABCC8-BC27-E611-B440-02163E013982.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/0A74517C-B827-E611-B4EF-02163E012A3B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/0A9EA573-B127-E611-9812-02163E01416E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/0C9C25E6-B427-E611-AC62-02163E011C11.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/0EFB86FB-B427-E611-8C4E-02163E01433F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/105C9E7E-BC27-E611-851F-02163E011D6B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/108D75AB-B927-E611-91AE-02163E01465A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/145D5F2B-BD27-E611-A234-02163E014527.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1614C49D-B427-E611-87B7-02163E0138C3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/16713032-C027-E611-A9A1-02163E011F09.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/16B3845D-B827-E611-BEDE-02163E014183.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/18C9A860-BF27-E611-AE22-02163E0134F2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1A4F8A8D-BF27-E611-B7E1-02163E011835.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1ABCD160-B527-E611-9F2D-02163E014606.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1C857726-C027-E611-ADF2-02163E012BC3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1CED3097-B527-E611-A174-02163E014693.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1CFCFB4E-BF27-E611-92FA-02163E0125F4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1E64C46E-B827-E611-9105-02163E011B1D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1E65F756-BF27-E611-BAE2-02163E011B18.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1EF1E390-BC27-E611-A9DF-02163E0140EC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/1EFCB912-B927-E611-9DF2-02163E0135CF.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/200DBF32-B827-E611-9E3F-02163E014776.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/2451EB61-BF27-E611-ABC7-02163E0141B9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/2628BD7A-BF27-E611-9130-02163E01376A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/262F013E-B127-E611-BCBF-02163E013759.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/26FAFC75-BC27-E611-A98A-02163E0118B6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/2A0DB1E9-C827-E611-B9BA-02163E0144E8.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/2A2ACABC-B527-E611-9AAF-02163E01461D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/2ED0E1AC-B827-E611-8F27-02163E014342.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/30360313-BA27-E611-A60E-02163E013546.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/32363F70-BF27-E611-9BD3-02163E01424F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/328BD930-B527-E611-A88A-02163E0145EB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/341088CA-B827-E611-A394-02163E011FA5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/36433864-BC27-E611-A4B3-02163E011C01.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/36AE820B-B527-E611-84B7-02163E0125EC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/380C1DBC-B927-E611-A075-02163E0144CC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/3A99B518-C727-E611-B1D2-02163E011E74.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/3CE8E882-BF27-E611-8E60-02163E014717.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/3E259599-B827-E611-9FA3-02163E014145.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4057DB27-BF27-E611-8850-02163E0129DC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/40F71504-BD27-E611-97CE-02163E014207.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/420AF31F-C827-E611-92DE-02163E011E30.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4225DE5E-BF27-E611-A538-02163E0134E8.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/425AF268-BC27-E611-A222-02163E0118E1.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4450EECC-B927-E611-8DCF-02163E0144D0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/446BB1B0-C027-E611-80A0-02163E0126BF.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4472BC63-BF27-E611-9DF6-02163E0135AA.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4A0DEC6C-B827-E611-B3F0-02163E0142DE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4A86E162-B827-E611-BB02-02163E0135CD.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4ADA506C-B927-E611-AA03-02163E014655.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4C4AE24B-C727-E611-AD45-02163E0144E8.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4CD87271-BF27-E611-8D40-02163E012A35.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4E3E1855-BF27-E611-9331-02163E0133EE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/4E79F39A-BD27-E611-B444-02163E01475A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5231B188-BF27-E611-9B6E-02163E014324.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5237DCE3-BF27-E611-B342-02163E0139A0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5295BEDF-BF27-E611-B886-02163E0134B2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/54B144CF-B827-E611-BB19-02163E012032.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/562361B1-B927-E611-8A7F-02163E0137B3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/56452844-B627-E611-9A0B-02163E01420A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/58F182BE-BF27-E611-B5BE-02163E0143F3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5A7F400E-B427-E611-8EFD-02163E011CC4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5C09083E-B827-E611-85A9-02163E0141B9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5C280183-BF27-E611-83FE-02163E011B9C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5C858317-BA27-E611-9795-02163E013630.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5E89D666-BC27-E611-AD2A-02163E013546.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/5EBBB33F-B627-E611-B519-02163E013747.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/60BE9D68-BC27-E611-AC7A-02163E011EB9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/625C861B-BD27-E611-B305-02163E01434D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6469DD28-B827-E611-AF0E-02163E011912.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/64E5C680-B427-E611-B666-02163E01215E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/64E8422E-BF27-E611-89F9-02163E01369B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6634DF5C-BF27-E611-8329-02163E011920.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/68940297-B927-E611-BEFF-02163E013747.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/68DC6545-C427-E611-98EB-02163E01343A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6A27FB0F-C227-E611-9918-02163E011FAB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6C37F600-B527-E611-8452-02163E0134FE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6CD5BF3B-B827-E611-A6B5-02163E012B47.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6E333FFA-BA27-E611-93E8-02163E0145EF.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6E80A9B2-B927-E611-871A-02163E01430A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/6ED91B0B-B927-E611-9C02-02163E0144FC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/70562AF1-B827-E611-ADF3-02163E0137D0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/70DAB684-BA27-E611-8E02-02163E014518.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/72445EAA-B827-E611-B4EE-02163E014285.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/7414323F-BF27-E611-865A-02163E011BF0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/74943168-BC27-E611-847E-02163E0133E7.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/7A28ABB1-B927-E611-A440-02163E011EC5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/7CCEA3F8-B827-E611-BB64-02163E0139DB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/7E95495F-B627-E611-A10A-02163E01474F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/829D5C02-BD27-E611-938C-02163E0133C6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/84356B9B-BC27-E611-BAA1-02163E011DF3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/868E699B-B827-E611-B1C1-02163E014475.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/86901A6E-BF27-E611-8504-02163E011FEA.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/88071389-BF27-E611-A9F9-02163E01343A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8A0A8571-BF27-E611-8C1F-02163E01386B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8AFCCB8A-B827-E611-9F9A-02163E011A0F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8C375029-BD27-E611-8EDF-02163E014590.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8CA75539-C427-E611-B431-02163E01348B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8E523741-BF27-E611-A29A-02163E0128EA.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8EAE079E-BD27-E611-A17A-02163E01432B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/8EE0E027-BF27-E611-BB09-02163E0134FE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/901CD7B3-B827-E611-B549-02163E011EC5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/9239ED8D-B827-E611-995C-02163E012AFA.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/92B86ECF-BC27-E611-9624-02163E014336.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/94EBFF26-B827-E611-B8B5-02163E0138C3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/96B8908B-BC27-E611-9483-02163E0141A3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/96C8295D-BF27-E611-88A2-02163E0138EE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/9817637A-B827-E611-81E9-02163E011CA0.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/982FE510-BF27-E611-B4BC-02163E011AF9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/98D0DE0D-B927-E611-B1E5-02163E014529.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/9CDA3A64-BC27-E611-89F9-02163E0140ED.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/9E88E074-BF27-E611-9DDA-02163E0119A1.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/9EB86DB2-BF27-E611-82C7-02163E0143BC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/9EDEB01E-BD27-E611-930A-02163E0142B9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A009BAB0-B827-E611-A6EB-02163E0145F5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A0C1817C-B827-E611-A00C-02163E0143B3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A25A7420-B927-E611-A644-02163E013785.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A4314EF6-BC27-E611-B8E6-02163E0138DD.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A44B624D-BA27-E611-B3C8-02163E0139DB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A6274D94-B927-E611-8D5D-02163E014696.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A6DE0832-B827-E611-99B1-02163E01422B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A6E6F5F8-BF27-E611-ACDB-02163E013901.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A80E1617-C127-E611-AA99-02163E012807.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/A8C47D29-B927-E611-9F0E-02163E0141F2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/AE207DC4-B727-E611-A32E-02163E01469F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B0C4B775-BC27-E611-BD19-02163E013513.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B244526A-BF27-E611-B34C-02163E011ACC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B29766EE-BF27-E611-A0B7-02163E0137EE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B2A1B875-B927-E611-8F8E-02163E014629.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B40835E1-B827-E611-8DA8-02163E014404.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B4198E66-BF27-E611-A973-02163E014603.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B47F7BD4-BC27-E611-8944-02163E0145F4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B485ADB0-BC27-E611-ACAA-02163E014175.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B4DC317A-B827-E611-B0E4-02163E0141EB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B4F02E1C-C927-E611-97FF-02163E011EE2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B68BBD63-BF27-E611-9F59-02163E01454B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B6B802CE-BF27-E611-897E-02163E0137CB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B6E72EB3-C027-E611-9834-02163E011B27.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B81C850E-B527-E611-915A-02163E011967.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/B8450977-B827-E611-B34F-02163E011D80.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/BAF0350D-C127-E611-B23E-02163E014159.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/BAF309C4-BF27-E611-B941-02163E014123.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/BE438149-BF27-E611-93C2-02163E011C8D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/BEDC728F-BC27-E611-BE9F-02163E0139D6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C0072852-B827-E611-ABBE-02163E014616.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C0C38F90-BF27-E611-81CC-02163E012BC3.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C2323857-BC27-E611-B817-02163E011FD6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C2E0AB3C-BA27-E611-A232-02163E0138EF.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C4AA6536-B827-E611-9386-02163E011A7D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C4ABDAC2-BF27-E611-81DC-02163E014450.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C4C3B282-BF27-E611-A8C3-02163E0141C2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C8520596-BC27-E611-85E5-02163E013427.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/C862826D-BC27-E611-84F1-02163E0135F2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CA084C27-B427-E611-A2E5-02163E011C8D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CA94F5BF-B827-E611-80A8-02163E013637.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CAABE681-BC27-E611-9B5B-02163E014383.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CAF59746-B127-E611-A62D-02163E0121C2.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CAF83984-BF27-E611-A296-02163E011FCE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CCA6C174-BF27-E611-AFC6-02163E011B1A.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CE421204-B527-E611-8F88-02163E01411F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CE86AC87-BC27-E611-93C7-02163E011894.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/CEA4B380-BC27-E611-81F4-02163E014212.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D01FC03B-B927-E611-8921-02163E014282.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D076FBA3-BE27-E611-9541-02163E0138EE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D0E97F76-B827-E611-8307-02163E0142A9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D23A50DB-BC27-E611-B016-02163E012BE5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D44B7A76-BC27-E611-9CB4-02163E01348B.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D675BD8B-BF27-E611-8A2D-02163E01383E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D85AA746-B127-E611-A591-02163E014446.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/D8A0F38D-BE27-E611-9A67-02163E01343C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/DA0BCC2A-BE27-E611-8440-02163E014590.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/DA1180BF-BF27-E611-AC31-02163E01445D.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/DA400133-BF27-E611-8838-02163E01343C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/DA7D4D47-B827-E611-9DD1-02163E0136C4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/DE238EA2-B827-E611-805A-02163E01223F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/E0A9100C-C727-E611-A2DF-02163E0145D4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/E2AE766C-B827-E611-95B0-02163E011B40.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/E4525593-BC27-E611-A9C9-02163E01215E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/E461B91F-BD27-E611-B7EE-02163E0145EC.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/E8DE3F42-C027-E611-9142-02163E012864.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/EC074F98-BF27-E611-B195-02163E01460E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/EC500C90-BC27-E611-AC4D-02163E013576.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/EE0CF69B-B827-E611-9964-02163E0145C9.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/EE40AF4C-B627-E611-B426-02163E013607.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/EE4B2F1A-B827-E611-BA56-02163E011DEE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/EEE80758-BE27-E611-9D04-02163E0141A4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F04353F1-C727-E611-A1DE-02163E0118D8.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F2C58064-BC27-E611-9C8F-02163E013989.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F4977FD5-B927-E611-97B3-02163E0133DB.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F49E78D7-BC27-E611-A330-02163E01470E.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F4D9BBD9-B927-E611-B93A-02163E0145D4.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F4E4302E-C227-E611-9E44-02163E0118B6.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F6A885C5-BF27-E611-A04C-02163E014293.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F6F794AB-BC27-E611-91E2-02163E0135D5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F810DF7F-BF27-E611-BEFF-02163E0120FE.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F816F556-B827-E611-8DEF-02163E013557.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/F84F35A5-B927-E611-8FE7-02163E0138F5.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/FA23C9CB-BF27-E611-BE59-02163E01467F.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/FC2AD12A-C327-E611-910D-02163E01463C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/FE02B4C6-BF27-E611-A689-02163E0128BA.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/FE0DD592-B827-E611-BA96-02163E01237C.root',
	'/store/express/Run2016B/ExpressPhysics/FEVT/Express-v2/000/274/284/00000/FE120469-B827-E611-A046-02163E011A55.root',
]
