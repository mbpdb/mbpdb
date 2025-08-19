from glob import glob
import string
from os.path import splitext
from time import strftime
from csv import writer



class SamplewiseSequenceAligner:

# Description:
#     Given a CSV file that contains all peptide-peptideSource-volume info,
#     and a set of FASTA input files for one or multiple proteins,
#     Find the volume intensity statistics
#         for every amino acid in every protein.
#     And write the results in CSV format
#     in a format of both one amino acid per line and ten amino acids per line.
#
# Author:
#     Michael Xin Sun: xinsun@ucdavis.edu
#     at 01:50:37am, Tue, Feb 19, 2013
#
# Possible bug from the inputCSV provider:
#     I used to have an issue which takes something like
#     "sp|P05814|CASB_HUMAN" and ""sp|P05814|CASB_HUMAN"
#     to be two different protein IDs (see a quotation mark there?)
#     This issue comes from the bug who outputs the CSV for our input CSV
#     If you see two proteinIDs in the result CSV files
#     that only differs from a punctuation mark such as ",
#     feel free to email me so that I can fix this issue.



    def __init__(self, config):

        self.config = config
        self.csvInputFileName = config["csvInputFile"]
        self.keepZeroIntensities = config["keepZeroIntensities"]

        self.listOfSampleNames = []

        # Set up a dictionary
        # to store all key-value pairs of
        # proteinID and proteinDescription
        self.proteinDescriptionDict = {}

        """
        proteinDescriptionDict = {proteinID1: proteinID1Description,
                                  proteinID2: proteinID2Description,
                                  proteinID3: proteinID3Description}
                                  ......}
        """
        # Set up a dictionary
        # to store all key-value pairs of
        # proteinID and proteinSequence
        self.proteinSequenceDict = {}

        """
        proteinSequenceDict = {proteinID1: proteinSequence1,
                               proteinID2: proteinSequence2,
                               proteinID3: proteinSequence3,
                               ......}
        """
        # Set up a dictionary
        # to store all peptide info in the input CSV
        # which includes
        # peptideSource
        # peptideSequence
        # peptideVolume
        self.peptideInfoDict = {}

        """
        peptide info hierarchy:
        peptide source
            -> peptide sample name
                -> peptide number of phosphorylation sites
                    -> peptide sequence
                        -> peptide volume

        peptideInfoDict = {
            peptideSource1: {
                peptideSample1: {
                    peptideNumberOfPhosphorylationSites1: {
                        peptideSequence1:
                            peptideVolume1,
                        peptideSequence2:
                            peptideVolume2,
                        ...
                    }
                    peptideNumberOfPhosphorylationSites2: {
                        peptideSequence3:
                            peptideVolume3,
                        peptideSequence4:
                            peptideVolume4,
                        ...
                    }
                    ...
                }
                peptideSample2: {
                    peptideNumberOfPhosphorylationSites3: {
                        peptideSequence5:
                            peptideVolume5,
                        eptideSequence6:
                            peptideVolume6,
                        ...
                    }
                    peptideNumberOfPhosphorylationSites4: {
                        peptideSequence7:
                            peptideVolume7,
                        peptideSequence8:
                            peptideVolume8,
                        ...
                    }
                    ...
                }
                ...
            }
            peptideSource2: {
                peptideSample3: {
                    peptideNumberOfPhosphorylationSites5: {
                        peptideSequence9:
                            peptideVolume9,
                        peptideSequence10:
                            peptideVolume10,
                        ...
                    }
                    peptideNumberOfPhosphorylationSites6: {
                        peptideSequence11:
                            peptideVolume11,
                        peptideSequence12:
                            peptideVolume12,
                        ...
                    }
                    ...
                }
                peptideSample4: {
                    peptideNumberOfPhosphorylationSites7: {
                        peptideSequence13:
                            peptideVolume13,
                        eptideSequence14:
                            peptideVolume14,
                        ...
                    }
                    peptideNumberOfPhosphorylationSites8: {
                        peptideSequence15:
                            peptideVolume15,
                        peptideSequence16:
                            peptideVolume16,
                        ...
                    }
                    ...
                }
                ...
            }
            ...
        }

        """
        # Set up a dictionary
        # to store every volume for every amino acid in every parent protein
        self.proteinVolumeDict = {}

        """
        PREVIOUS: no sample names, no number of phosphorylation sites

        proteinVolumeDict = {proteinID1: ["zero",
                                          volumeForAA1inProteinID1,
                                          volumeForAA2inProteinID1,
                                          ...]
                             proteinID2: ["zero",
                                          volumeForAA1inProteinID2,
                                          volumeForAA2inProteinID2,
                                          ...]
                             }
        """

        """
        NOW: with sample names, with number of phosphorylation sites

        proteinVolumeDict = {
            proteinID1: {
                peptideSample1: {
                    peptideNumberOfPhosphorylationSites1:
                        ["zero",
                         volumeForAA1inProteinID1,
                         volumeForAA2inProteinID1,
                         ...],
                    peptideNumberOfPhosphorylationSites2:
                        ["zero",
                         volumeForAA1inProteinID1,
                         volumeForAA2inProteinID1,
                         ...],
                    ...
                }
                peptideSample2: {
                    peptideNumberOfPhosphorylationSites3:
                        ["zero",
                         volumeForAA1inProteinID1,
                         volumeForAA2inProteinID1,
                         ...],
                    peptideNumberOfPhosphorylationSites4:
                        ["zero",
                         volumeForAA1inProteinID1,
                         volumeForAA2inProteinID1,
                         ...],
                    ...
                }
                ...
            }
            proteinID2: {
                peptideSample3: {
                    peptideNumberOfPhosphorylationSites5:
                        ["zero",
                         volumeForAA1inProteinID2,
                         volumeForAA2inProteinID2,
                         ...],
                    peptideNumberOfPhosphorylationSites6:
                        ["zero",
                         volumeForAA1inProteinID2,
                         volumeForAA2inProteinID2,
                         ...],
                    ...
                }
                peptideSample4: {
                    peptideNumberOfPhosphorylationSites7:
                        ["zero",
                         volumeForAA1inProteinID2,
                         volumeForAA2inProteinID2,
                         ...],
                    peptideNumberOfPhosphorylationSites7:
                        ["zero",
                         volumeForAA1inProteinID2,
                         volumeForAA2inProteinID2,
                         ...],
                    ...
                }
                ...
            }
            ...
        }

        """
        self.peptideVolumeContributionDict = {}

        """
        with sample names, with number of phosphorylation sites

        peptideVolumeContributionDict = {
            peptideSource1: {
                peptideSample1: {
                    peptideNumberOfPhosphorylationSites1: {
                        peptideString1: [0,   0, 30,  0, ...],
                        peptideString2: [0,  20, 20,  0, ...],
                        ...
                    }
                    peptideNumberOfPhosphorylationSites2: {
                        peptideString1: [15, 15,  0,  0, ...],
                        peptideString2: [10, 10, 10,  0, ...],
                        ...
                    }
                    ...
                }
                peptideSample2: {
                    peptideNumberOfPhosphorylationSites3: {
                        peptideString1: [10, 10, 20,  0, ...],
                        peptideString2: [10, 15, 30, 10, ...],
                        ...
                    }
                    peptideNumberOfPhosphorylationSites4: {
                        peptideString1: [25, 55, 30, 10, ...],
                        peptideString2: [20, 15, 30, 10, ...],
                        ...
                    }
                    ...
                }
                ...
            }
            peptideSource2: {
                peptideSample3: {
                    peptideNumberOfPhosphorylationSites5: {
                        peptideString1: [0,   0, 40,  0, ...],
                        peptideString2: [0,  30, 30,  0, ...],
                        ...
                    }
                    peptideNumberOfPhosphorylationSites6: {
                        peptideString1: [25, 25,  0,  0, ...],
                        peptideString2: [20, 20, 20,  0, ...],
                        ...
                    }
                    ...
                }
                peptideSample4: {
                    peptideNumberOfPhosphorylationSites7: {
                        peptideString1: [20, 20, 30,  0, ...],
                        peptideString2: [20, 25, 40, 20, ...],
                        ...
                    }
                    peptideNumberOfPhosphorylationSites8: {
                        peptideString1: [35, 65, 40, 20, ...],
                        peptideString2: [30, 25, 40, 20, ...],
                        ...
                    }
                    ...
                }
                ...
            }
            ...
        }

        """


    def readFromFastas(self):

        # Function Description:
        #     Read and parse all FASTA input files
        #     that contains the parent protein information
        # Function Input:
        #     FASTA input files
        # Function Output:
        #     None

        # print("Reading and Parsing fasta input files...")

        # Get the list of input file names
        # All files with extension
        # ".fasta", ".fa", ".fna", ".fsa" and ".mpfa"
        # are considered valid FASTA input files
        # The file extension listed here are case-insensitive
        # So ".fasta", ".Fasta", ".FASTA" will all be valid
        listOfFastaFileNames = [fastaFileName
                                for fastaFileName in glob("/var/www/peptide/include/peptide/scripts/pySamplewiseSequenceAligner_v1.2/fasta_input_files/*.*")
                                if (".fasta" in fastaFileName.lower() or
                                    ".fa" in fastaFileName.lower() or
                                    ".fna" in fastaFileName.lower() or
                                    ".fsa" in fastaFileName.lower() or
                                    ".mpfa" in fastaFileName.lower() or
                                       (".txt" in fastaFileName.lower() and
                                            (".fasta" in fastaFileName.lower() or
                                             ".fa" in fastaFileName.lower() or
                                             ".fna" in fastaFileName.lower() or
                                             ".fsa" in fastaFileName.lower() or
                                             ".mpfa" in fastaFileName.lower())))]

        self.listOfFastaFileNames = listOfFastaFileNames

        # For every FASTA file name in the lsit of all fasta file names:
        #     Read in data from single FASTA file
        for fastaFileName in listOfFastaFileNames:
            self.readFromSingleFasta(fastaFileName)

        # print("Done.\n\n")



    def readFromSingleFasta(self, fastaFileName):

        # Function Description
        #     Read and parse a single FASTA input file
        #     that contains the parent protein information
        # Function Input:
        #     The file name of the single FASTA file
        # Function Output:
        #     None

        proteinDescriptionDict = self.proteinDescriptionDict
        proteinSequenceDict = self.proteinSequenceDict

        # print("Reading and Parsing single fasta input file " + fastaFileName
              + "...")

        # Open one FASTA input file to read
        inFasta = open(fastaFileName, "r")
        fastaFirstLine = inFasta.readline()

        if fastaFirstLine[0] != ">":
            raise Exception("Error: Possibly corrupted FASTA file "
                            + fastaFileName + ": does NOT begin with '>'.")

        firstLineFields = fastaFirstLine.strip().split()

        # Read in proteinID for this FASTA input file
        proteinID = firstLineFields[0][1:]

        # Read in proteinDescription for this FASTA input file
        proteinDescription = " ".join([word
                                       for word in firstLineFields[1:]])

        # Set up the key-value pair for proteinID and proteinDescription
        proteinDescriptionDict[proteinID] = proteinDescription

        # Get the entire protein sequence in this FASTA input file
        proteinSequence = "".join([line.strip()
                                   for line in inFasta])

        inFasta.close()

        # Error out if we find one proteinID which has been already read
        if proteinID in proteinSequenceDict.keys():
            raise Exception("Error: Possibly repetitive FASTA file "
                            + fastaFileName
                            + ": repetitive protein ID '" + proteinID + ".")

        # Error out if the first letter in the protein sequence
        #     is not an uppercase letter
        # which means the FASTA file is possibly corrupted
        if proteinSequence[0] not in string.ascii_uppercase:
            raise Exception("Error: Possibly corrupted FASTA file "
                            + fastaFileName + ": second line does NOT begin with"
                            + "a capital letter for start point amino acid.")

        # append proteinSequence to " "
        # so that index 1 in proteinSequence in programming string
        # is the same as index 1 in proteinSequence in daily life
        proteinSequenceDict[proteinID] = " " + proteinSequence

        self.proteinDescriptionDict = proteinDescriptionDict
        self.proteinSequenceDict = proteinSequenceDict

        # print("Done.")



    def readFromCsv(self):

        # Function Description:
        #     Read and parse CSV input file
        #     that contains peptide information,
        #     such as peptide sequence, peptide source and peptide volume
        # Function Input:
        #     Input CSV file that contains peptide information
        # Function Output:
        #     None

        peptideInfoDict = self.peptideInfoDict
        proteinSequenceDict = self.proteinSequenceDict
        listOfSampleNames = self.listOfSampleNames
        csvInputFileName = self.csvInputFileName

        numberOfPhosphorylationsAllowed = self.config["numberOfPhosphorylationsAllowed"]

        print("Reading and Parsing CSV input file" + csvInputFileName + "...")

        # Open CSV input file to read
        inCsv = open(csvInputFileName, "r")

        # Get the first line of csv input as header info
        csvFirstLine = inCsv.readline()
        csvHeaders = csvFirstLine.strip().split(",")

        # Variable of key-value pairs for column headers and column indices,
        # Which means the order of "Name", "Volumen", "Notes", "Sample", "Phospho"
        #     and other columns simply doesn't matter.
        csvHeaderColumnLookupDict = {}

        """
        csvHeaderColumnLookupDict = {"Name": someColumnNumberForName,
                                     "Volumen": someColumnNumberForVolumen,
                                     "Notes": someColumnNumberForNotes,
                                     "Sample": someColumnNumberForSample,
                                     "Phospho": someColumnNumberForPhospho,
                                     ......}
        """
        # Build key-value pairs for column headers and column indices
        for csvHeaderIndex in range(len(csvHeaders)):
            csvHeader = csvHeaders[csvHeaderIndex]
            if csvHeader in ["Name", "Volumen", "Notes", "Sample", "Phospho"]:
                if csvHeader in csvHeaderColumnLookupDict.keys():
                    raise Exception("Error: Possibly corrupted CSV file: "
                                    + "There are at least 2 columns with name '"
                                    + csvHeader + "'.")
                csvHeaderColumnLookupDict[csvHeader] = csvHeaderIndex
            else:
                raise Exception(csvHeader + " is an unknown header.")

        # Get all column indices for "Name", "Volumen", "Notes", "Sample" and "Phospho"
        # In the default case,
        # "Name" is the 1st column
        # "Volumen" is the 2nd column
        # "Notes" is the 3rd column
        # "Sample" is the 4th column
        # "Phospho" is the 5th column
        nameHeaderIndex = csvHeaderColumnLookupDict["Name"]
        volumenHeaderIndex = csvHeaderColumnLookupDict["Volumen"]
        notesHeaderIndex = csvHeaderColumnLookupDict["Notes"]
        sampleHeaderIndex = csvHeaderColumnLookupDict["Sample"]
        numberOfPhosphorylationSitesHeaderIndex = csvHeaderColumnLookupDict["Phospho"]

        # Read all peptide source, peptide sequence, peptide sample name,
        # peptide number of phosphorylation sites and peptide volume info
        # from the input CSV file

        for line in inCsv:

            fields = line.strip().split(",")

            peptideSource = fields[notesHeaderIndex].strip().split(";")[0].replace('"', "")
            peptideSample = fields[sampleHeaderIndex].strip()
            peptideNumberOfPhosphorylationSites = fields[
                    numberOfPhosphorylationSitesHeaderIndex].strip()
            #peptideNumberOfPhosphorylationSites = int(fields[
            #        numberOfPhosphorylationSitesHeaderIndex].strip())
            #if peptideNumberOfPhosphorylationSites not in numberOfPhosphorylationsAllowed:
            #    continue
            peptideSequence = fields[nameHeaderIndex].strip()
            peptideVolume = int(fields[volumenHeaderIndex].strip())

            """
            if peptideSequence not in listOfPeptideSequences:
                listOfPeptideSequences.append(peptideSequence)

            """
            if peptideSource in proteinSequenceDict.keys():
                proteinSequence = proteinSequenceDict[peptideSource]
            else:
                raise Exception(peptideSource + " is an unknown peptide.")

            if peptideSource not in peptideInfoDict.keys():
                peptideInfoDict\
                        [peptideSource]\
                        = {}
            if peptideSample not in listOfSampleNames:
                listOfSampleNames.append(peptideSample)
            if peptideSample not in peptideInfoDict[peptideSource].keys():
                peptideInfoDict\
                        [peptideSource]\
                        [peptideSample]\
                        = {}
            if peptideNumberOfPhosphorylationSites not in \
                    peptideInfoDict\
                            [peptideSource]\
                            [peptideSample]\
                            .keys():
                peptideInfoDict\
                        [peptideSource]\
                        [peptideSample]\
                        [peptideNumberOfPhosphorylationSites]\
                        = {}
            if peptideSequence not in \
                    peptideInfoDict\
                            [peptideSource]\
                            [peptideSample]\
                            [peptideNumberOfPhosphorylationSites]\
                            .keys():
                peptideInfoDict\
                        [peptideSource]\
                        [peptideSample]\
                        [peptideNumberOfPhosphorylationSites]\
                        [peptideSequence]\
                        = peptideVolume
            else:
                peptideInfoDict\
                        [peptideSource]\
                        [peptideSample]\
                        [peptideNumberOfPhosphorylationSites]\
                        [peptideSequence]\
                        += peptideVolume

        inCsv.close()

        """
        self.listOfPeptideSequences = listOfPeptideSequences

        """
        self.peptideInfoDict = peptideInfoDict
        self.listOfSampleNames = listOfSampleNames
        #print(listOfSampleNames)

        print("Done.\n\n")



    def alignSequences(self):

        # Function Description
        #     Align and match peptide strings to protein strings
        #     And add up all the volume intensities
        #     for every amino acid for every protein
        #     in an amino-acid-wise way
        # Function Input:
        #     None
        # Function Output:
        #     None

        peptideInfoDict = self.peptideInfoDict
        proteinSequenceDict = self.proteinSequenceDict
        proteinVolumeDict = self.proteinVolumeDict
        listOfSampleNames = self.listOfSampleNames

        # Initialize proteinVolumeDict
        for peptideSource in peptideInfoDict.keys():
            if peptideSource in proteinSequenceDict.keys():
                proteinSequence = proteinSequenceDict[peptideSource]
            else:
                raise Exception("Peptide info not found for " + peptideSource)
            if peptideSource not in proteinVolumeDict.keys():
                proteinVolumeDict\
                        [peptideSource]\
                     = {}
            for peptideSample in peptideInfoDict[peptideSource].keys():
                if peptideSample not in proteinVolumeDict[peptideSource].keys():
                    proteinVolumeDict\
                            [peptideSource]\
                            [peptideSample] = {}
                for peptideNumberOfPhosphorylationSites in \
                        peptideInfoDict\
                                [peptideSource]\
                                [peptideSample].keys():
                    if peptideNumberOfPhosphorylationSites not in \
                            proteinVolumeDict\
                                    [peptideSource]\
                                    [peptideSample].keys():
                        proteinVolumeDict\
                                [peptideSource]\
                                [peptideSample]\
                                [peptideNumberOfPhosphorylationSites]\
                                = ["zero"] + [0] * (len(proteinSequence) - 1)

        #print(proteinVolumeDict)
        """
        # Initialize peptideVolumnContributionDict
        for peptideSource in peptideInfoDict.keys():
            proteinSequence = proteinSequenceDict[peptideSource]
            if peptideSource not in peptideVolumeContributionDict.keys():
                peptideVolumeContributionDict\
                        [peptideSource]\
                        = {}
            else:
                for peptideSample in peptideInfoDict[peptideSource].keys():
                    if peptideSample not in peptideVolumeContributionDict.keys():
                        peptideVolumeContributionDict\
                                [peptideSource]\
                                [peptideSample]\
                                = {}
                    else:
                        for peptideNumberOfPhosphorylationSites in \
                                peptideInfoDict\
                                        [peptideSource]\
                                        [peptideSample].keys():
                            if peptideNumberOfPhosphorylationSites not in \
                                    peptideVolumeContributionDict\
                                            [peptideSource]\
                                            [peptideSample].keys():
                                peptideVolumeContributionDict\
                                        [peptideSource]\
                                        [peptideSample]\
                                        [peptideNumberOfPhosphorylationSites]\
                                        = {}
                            else:
                                for peptideSequence in peptideInfoDict\
                                        [peptideSource]\
                                        [peptideSample]\
                                        [peptideNumberOfPhosphorylationSites].keys():
                                    if peptideSequence not in \
                                            peptideVolumeContributionDict\
                                                    [peptideSource]\
                                                    [peptideSample]\
                                                    [peptideNumberOfPhosphorylationSites].keys():
                                        peptideVolumeContributionDict\
                                                [peptideSource]\
                                                [peptideSample]\
                                                [peptideNumberOfPhosphorylationSites]\
                                                [peptideSequence]\
                                                = ["zero"] + [0] * (len(proteinSequence) - 1)
                                    else:
                                        pass

        """

        # Add up the volume intensity values
        #     for every amino acid in every parent protein
        for peptideSource in peptideInfoDict.keys():
            proteinSequence = proteinSequenceDict[peptideSource]
            for peptideSample in peptideInfoDict[peptideSource].keys():
                for peptideNumberOfPhosphorylationSites in \
                        peptideInfoDict[peptideSource]\
                                       [peptideSample].keys():
                    for peptideSequence in \
                            peptideInfoDict\
                                    [peptideSource]\
                                    [peptideSample]\
                                    [peptideNumberOfPhosphorylationSites].keys():
                        peptideVolume = peptideInfoDict\
                                                [peptideSource]\
                                                [peptideSample]\
                                                [peptideNumberOfPhosphorylationSites]\
                                                [peptideSequence]
                        matchedProteinStartingIndices = self.findAllSubstringIndices(
                                proteinSequence, peptideSequence)

                        aminoAcidVolume = round(peptideVolume / len(
                                                matchedProteinStartingIndices))
                        for i in matchedProteinStartingIndices:
                            for offset in range(len(peptideSequence)):
                                proteinVolumeDict\
                                        [peptideSource]\
                                        [peptideSample]\
                                        [peptideNumberOfPhosphorylationSites]\
                                        [i + offset]\
                                        += aminoAcidVolume

        self.proteinVolumeDict = proteinVolumeDict
        #print(proteinVolumeDict)
        #print(self.peptideVolumeContributionDict.keys())
        self.csvInputFileName = self.csvInputFileName.split("/")[-1]

        #for peptideSource in self.peptideVolumeContributionDict.keys():
        #    print(self.peptideVolumeContributionDict[peptideSource])



    def findAllSubstringIndices(self, parentString, subString):

        # Function Description:
        #     A TOY PROGRAM
        #     for all strings that is a substring of the parentString:
        #         return a list of substring-start indices
        #     the set of all substrings may overlap
        #
        #     for example:
        #         Input: "ABCDABC" and "ABC"
        #         Output: [0, 4]
        #     for example:
        #         Input: "ABCBCBCD" AND "BCBC"
        #         Output: [1, 3]
        #
        # Function Input:
        #     A parent string
        #     A subString
        # Function Output:
        #     A list of substring-start indices

        listIndex = []
        index = parentString.find(subString)
        while index >= 0:
            listIndex.append(index)
            index = parentString.find(subString, index + 1)
        return listIndex



    def writeToCsvOneAAPerLine(self, csv_output_path):

        # Function Description:
        #     Write all peptide matching results of all proteins
        #     into a CSV output file
        #     in a format of one amino acid per line
        # Function Input:
        #     None
        # Function Output:
        #     A CSV output file that contains all peptide matching results of all proteins

        proteinDescriptionDict = self.proteinDescriptionDict
        proteinSequenceDict = self.proteinSequenceDict
        proteinVolumeDict = self.proteinVolumeDict
        peptideVolumeContributionDict = self.peptideVolumeContributionDict
        listOfSampleNames = self.listOfSampleNames
        numberOfPhosphorylationsAllowed = self.config["numberOfPhosphorylationsAllowed"]

        """
        print("\n".join(list(proteinDescriptionDict.keys())))
        print("")
        print("\n".join(list(proteinSequenceDict.keys())))
        print("")
        print("\n".join(list(proteinVolumeDict.keys())))
        print("")
        print("\n".join(list(peptideVolumeContributionDict.keys())))
        print("")

        """

        csvInputFileName = self.csvInputFileName

        print("Writing CSV output file, 1 amino acid per line...")

        print("where " + ', '.join([str(number)
                                for number in numberOfPhosphorylationsAllowed])
              + " phosphorylation sites are selected,")

        if self.keepZeroIntensities == True:
            print("Keeping all zero intensities...")
        else:
            print("Omitting all zero intensities...")

        # Add the date and time into the output file name
        if self.keepZeroIntensities == True:
            csvOutputFileName = ("CSV_1_" + splitext(csvInputFileName)[0]
                                 + "_protein_aa_volume_statistics_allowing_"
                                 + "_".join([str(number)
                                    for number in numberOfPhosphorylationsAllowed])
                                 + "_phosphorylations_including_zeros"
                                 + strftime("_%I_%M_%S_%p_%b_%d_%Y") + ".csv")
        else:
            csvOutputFileName = ("CSV_1_" + splitext(csvInputFileName)[0]
                                 + "_protein_aa_volume_statistics_allowing_"
                                 + "_".join([str(number)
                                    for number in numberOfPhosphorylationsAllowed])
                                 + "_phosphorylations_excluding_zeros"
                                 + strftime("_%I_%M_%S_%p_%b_%d_%Y") + ".csv")

        # Add "_1" to the output file name in case there's a name conflict
        listOfRepetitiveFileNames = [fileName
                                     for fileName in glob("*.csv")
                                     if fileName == csvOutputFileName]

        while listOfRepetitiveFileNames != []:
            baseOutput, extensionOutput = splitext(csvOutputFileName)
            csvOutputFileName = baseOutput + "_1" + extensionOutput

            listOfRepetitiveFileNames = [fileName
                                         for fileName in glob("*.csv")
                                         if fileName == csvOutputFileName]

        outCsv = open(csv_output_path + "/" + csvOutputFileName, "wb")
        csvWriter = writer(outCsv)

        # Write a description of the output file
        csvWriter.writerow(["This file contains protein amino acid volume intensity"])
        csvWriter.writerow(["that comes from csv file in the csv input folder"])
        csvWriter.writerow(["for all fasta input files in the fasta input folder"])

        csvWriter.writerow(["Number of Phosphorylation sites allowed: "
                            + ', '.join([str(number)
                                for number in numberOfPhosphorylationsAllowed])])

        if self.keepZeroIntensities == True:
            csvWriter.writerow(["Amino acids with 0 volume intensity are also listed"])
        else:
            csvWriter.writerow(["Amino acids with 0 volume intensity are OMITTED"])

        csvWriter.writerow(["Right Click and 'Sort by Name' in the fasta input folder"])
        csvWriter.writerow(["That's the order that all output are organized."])
        csvWriter.writerow([""])

        # Get the list of proteinIDs from FASTA input files
        listOfProteinIDsFromFasta = list(proteinSequenceDict.keys())

        # Sort all FASTA files by Name in alphabetical order
        # which is same as "Sort by Name" using Right Click
        for proteinIDFromFasta in sorted(listOfProteinIDsFromFasta):

            if proteinIDFromFasta in proteinVolumeDict.keys():

                # Write proteinID and proteinDescription
                # so you can identify which protein it is
                csvWriter.writerow([proteinIDFromFasta])
                csvWriter.writerow([proteinDescriptionDict[proteinIDFromFasta]])

                proteinSequence = proteinSequenceDict[proteinIDFromFasta]
                proteinVolumeInfo = proteinVolumeDict[proteinIDFromFasta]

                # Write a table header
                csvWriter.writerow(["", "AA Index", "AA", "Volume"] + listOfSampleNames)

                for aminoAcidIndex in range(1, len(proteinSequence)):

                    aminoAcidVolumeForAllSamples = 0
                    listOfAminoAcidVolumes = []

                    for peptideSample in listOfSampleNames:

                        aminoAcidVolumePerSample = 0

                        if peptideSample not in proteinVolumeInfo.keys():
                            aminoAcidVolumePerSample = 0
                        else:
                            for peptideNumberOfPhosphorylationSites in \
                                    proteinVolumeInfo[peptideSample].keys():

                                aminoAcidVolumePerSamplePerPhosphorylationSite\
                                        = proteinVolumeInfo\
                                                [peptideSample]\
                                                [peptideNumberOfPhosphorylationSites]\
                                                [aminoAcidIndex]
                                aminoAcidVolumePerSample \
                                        += aminoAcidVolumePerSamplePerPhosphorylationSite

                        aminoAcidVolumeForAllSamples += aminoAcidVolumePerSample
                        listOfAminoAcidVolumes.append(aminoAcidVolumePerSample)

                    if self.keepZeroIntensities == True:

                        #print(peptideVolumeContribution)
                        #print("HELLO")
                        csvWriter.writerow(["",
                                            aminoAcidIndex,
                                            proteinSequence[aminoAcidIndex],
                                            aminoAcidVolumeForAllSamples] +
                                            listOfAminoAcidVolumes)

                    else:

                        # Write volume info,
                        # one volume per line,
                        # as long as the volume is NOT 0
                        if aminoAcidVolumeForAllSamples != 0:
                            #print("Hi")
                            csvWriter.writerow(["",
                                                aminoAcidIndex,
                                                proteinSequence[aminoAcidIndex],
                                                aminoAcidVolumeForAllSamples] +
                                                listOfAminoAcidVolumes)

            else:

                # If one proteinID is NOT matched with any peptide
                #     Write "NOT MATCHED AT ALL"
                csvWriter.writerow([proteinIDFromFasta])
                csvWriter.writerow([proteinDescriptionDict[proteinIDFromFasta]])

                #csvWriter.writerow(["", "AA Index", "AA", "Volume"])
                csvWriter.writerow(["", "NOT", "MATCHED", "AT", "ALL"])

            csvWriter.writerow([""])

        outCsv.close()

        print("Done.\n\n")
