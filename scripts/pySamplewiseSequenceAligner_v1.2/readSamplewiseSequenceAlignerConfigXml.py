from xml.dom import minidom
import xml.parsers.expat as expat
import sys


class configuration(dict):

    def __init__(self, filename):

        try:
            # file = open("SamplewiseSequenceAlignerConfig.xml", "rb")
            file = open(filename, "rb")
            configDom = minidom.parse(file)
        except IOError:
            print("ioError: SamplewiseSequenceAlignerConfig.xml not found")
        #ExpatError generated when parsing XML fails
        except expat.ExpatError:
            print("SamplewiseSequenceAlignerConfig.xml not in XML format, or corrupted:")
            for entry in sys.exc_info():
                print(entry)

        try:
            sequenceAlignerConfigNode = configDom.getElementsByTagName(
                    "sequencealignerconfig")[0]
            csvInputFileNode = sequenceAlignerConfigNode.getElementsByTagName(
                    "csvinputfile")[0]
            csvInputFolder = csvInputFileNode.getAttribute("folder").strip()
            csvInputFile = csvInputFileNode.getAttribute("filename").strip()
        except IndexError:
            print("Missing 1 or more required configuration fields: folder or filename")
            for entry in sys.exc_info():
                print(entry)

        csvInputFullFolder = csvInputFolder + "/"
        csvInputFile = csvInputFullFolder + csvInputFile
        print(csvInputFile)
        
        self["csvInputFile"] = csvInputFile

        try:
            phosphorylationNode = sequenceAlignerConfigNode.getElementsByTagName(
                    "phosphorylation")[0]
            numberOfPhosphorylationsAllowed = phosphorylationNode.getAttribute("allowed")
            if numberOfPhosphorylationsAllowed == "":
                raise Exception("Number of phosphorylations cannot be empty")
            numberOfPhosphorylationsAllowed = numberOfPhosphorylationsAllowed.strip().strip(",")
            numberOfPhosphorylationsAllowed = [number.strip()
                    for number in numberOfPhosphorylationsAllowed.split(",")]
            #numberOfPhosphorylationsAllowed = [int(number.strip())
            #        for number in numberOfPhosphorylationsAllowed.split(",")]
        except IndexError:
            print("Missing 1 or more required configuration fields: ")
            for entry in sys.exc_info():
                print(entry)

        self["numberOfPhosphorylationsAllowed"] = numberOfPhosphorylationsAllowed

        try:
            keepZeroIntensitiesNode = sequenceAlignerConfigNode.getElementsByTagName(
                    "keepzerointensities")[0]
            keepZeroIntensities = bool(keepZeroIntensitiesNode.getAttribute("keep").strip())
        except IndexError:
            print("Missing 1 or more required configuration fields: keepzerointensities.keep")
            for entry in sys.exc_info():
                print(entry)
                
        self["keepZeroIntensities"] = keepZeroIntensities
        
