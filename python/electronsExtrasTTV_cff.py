import FWCore.ParameterSet.Config as cms

# All workingpoints we need to probe
workingPoints = ["TTVLoose","TTVLeptonMvaL","TTVLeptonMvaM","TTVLeptonMvaT","RTTVLeptonMvaL","RTTVLeptonMvaM","RTTVLeptonMvaT","TightCharge"]

#
# Sequence to add userfloats
#
def addTTVIDs(process, options):
    from PhysicsTools.NanoAOD.electrons_cff import isoForEle, ptRatioRelForEle, slimmedElectronsWithUserData 

    if options['is2016']: effAreas = 'RecoEgamma/ElectronIdentification/data/Spring15/effAreaElectrons_cone03_pfNeuHadronsAndPhotons_25ns.txt'
    else:                 effAreas = 'RecoEgamma/ElectronIdentification/data/Fall17/effAreaElectrons_cone03_pfNeuHadronsAndPhotons_92X.txt'

    process.isoForEle                = isoForEle
    process.isoForEle.rho_MiniIso    = cms.InputTag("fixedGridRhoFastjetAll")
    process.isoForEle.EAFile_MiniIso = cms.FileInPath(effAreas)
    process.isoForEle.EAFile_PFIso   = cms.FileInPath(effAreas)

    process.ptRatioRelForEle             = ptRatioRelForEle
    process.slimmedElectronsWithUserData = slimmedElectronsWithUserData

    # Make a new electron collection, with additional variables that are used for the LeptonMVA below
    process.slimmedElectronsWithUserData.src = cms.InputTag(options['ELECTRON_COLL'])
    process.slimmedElectronsWithUserData.userFloats = cms.PSet(
      miniIsoChg           = cms.InputTag("isoForEle:miniIsoChg"),
      miniIsoAll           = cms.InputTag("isoForEle:miniIsoAll"),
      PFIsoChg             = cms.InputTag("isoForEle:PFIsoChg"),
      PFIsoAll             = cms.InputTag("isoForEle:PFIsoAll"),
      ptRatio              = cms.InputTag("ptRatioRelForEle:ptRatio"),
      ptRel                = cms.InputTag("ptRatioRelForEle:ptRel"),
      jetNDauChargedMVASel = cms.InputTag("ptRatioRelForEle:jetNDauChargedMVASel"),
      closestJetDeepCsv    = cms.InputTag("ptRatioRelForEle:closestJetDeepCsv"),
    )
    process.slimmedElectronsWithUserData.userIntFromBools = cms.PSet() # Removed
    process.slimmedElectronsWithUserData.userInts         = cms.PSet() # Removed

    process.ttv_sequence = cms.Sequence(
      process.isoForEle +
      process.ptRatioRelForEle + 
      process.slimmedElectronsWithUserData 
    )

    process.ttvEleVarHelper = cms.EDProducer("TTVElectronVariableHelper",
      probes = cms.InputTag("slimmedElectronsWithUserData"),
      mvasGP = cms.InputTag("electronMVAValueMapProducer:ElectronMVAEstimatorRun2Spring16GeneralPurposeV1Values"),
      mvas   = cms.InputTag("electronMVAValueMapProducer:ElectronMVAEstimatorRun2Fall17NoIsoV1Values"),
      is2016 = cms.untracked.bool((True if options['is2016'] else False)),
    )


def getTreeSeqTTV(process):
    for wp in workingPoints:
      temp           = process.probeEleCutBasedVeto.clone()
      temp.selection = cms.InputTag('ttvEleVarHelper:pass' + wp)
      setattr(process, 'probes' + wp, temp)
      process.ele_sequence += temp

    def addProducer(name, ref, workingPointsForRef):
      goodElectrons           = process.goodElectrons.clone()
      goodElectrons.isAND     = cms.bool(False)
      goodElectrons.selection = cms.InputTag('probes' + ref)
      setattr(process, 'goodElectrons' + ref, goodElectrons)
      process.tag_sequence += goodElectrons

      probeEle        = process.probeEle.clone()
      probeEle.inputs = cms.InputTag('goodElectrons' + ref)
      setattr(process, 'probe' + ref, probeEle)
      process.ele_sequence += probeEle

      tnpPairing       = process.tnpPairingEleIDs.clone()
      tnpPairing.decay = cms.string('tagEle probe' + ref)
      setattr(process, 'tnpPairing' + ref, tnpPairing)
      process.tnpPairs_sequence *= tnpPairing

      producer = process.tnpEleIDs.clone()
      producer.jetCollection = cms.InputTag("slimmedJets")
      producer.jet_pt_cut    = cms.double(30.)
      producer.jet_eta_cut   = cms.double(2.5)
      producer.match_delta_r = cms.double(0.3)
      producer.tagProbePairs = cms.InputTag('tnpPairing' + ref)
      producer.allProbes     = cms.InputTag('probe' + ref)
      producer.flags         = cms.PSet()
      for wp in workingPointsForRef: setattr(producer.flags, 'passing' + wp, cms.InputTag('probes' + wp))

      setattr(process, name, producer)
      return producer

    treeSeq = cms.Sequence()
    treeSeq *= addProducer('EleToId',                    'Ele',            ['TTVLoose'])
    treeSeq *= addProducer('TTVLooseToLeptonMva',        'TTVLoose',       ['TTVLeptonMvaL','TTVLeptonMvaM','TTVLeptonMvaT'])
    treeSeq *= addProducer('TTVLeptonMvaLToTightCharge', 'RTTVLeptonMvaL', ['TightCharge'])
    treeSeq *= addProducer('TTVLeptonMvaMToTightCharge', 'RTTVLeptonMvaM', ['TightCharge'])
    treeSeq *= addProducer('TTVLeptonMvaTToTightCharge', 'RTTVLeptonMvaT', ['TightCharge'])
    return treeSeq
