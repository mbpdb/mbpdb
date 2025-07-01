from pySamplewiseSequenceAligner import *
from readSamplewiseSequenceAlignerConfigXml import configuration
import sys


# Run this file

# config = configuration("SamplewiseSequenceAlignerConfig.xml")
config = configuration(sys.argv[1])

samplewiseSequenceAligner = SamplewiseSequenceAligner(config)

samplewiseSequenceAligner.readFromFastas()

samplewiseSequenceAligner.readFromCsv()

samplewiseSequenceAligner.alignSequences()

samplewiseSequenceAligner.writeToCsvOneAAPerLine(sys.argv[2])

#sequenceAligner.writeToCsvTenAAsPerLine()
