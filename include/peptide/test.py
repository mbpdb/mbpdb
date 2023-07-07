#!/usr/bin/python

import sys
import os
from Bio import SeqIO

def make_dict_from_fasta_files(path):
    fdict = {}

    fasta_files = [os.path.join(path, f) for f in os.listdir(path)]
    for ff in fasta_files:
        for seq_record in SeqIO.parse(ff, "fasta"):
            protid = seq_record.id.split("|")[1]
            fdict[protid] = str(seq_record.seq)

    return fdict

if __name__ == "__main__":
    fasta_dict = make_dict_from_fasta_files(sys.argv[1])

    #for key, value in fasta_dict.iteritems():
        #print key, ":", value

    if str(sys.argv[2]) not in fasta_dict:
        print str(sys.argv[2]), "not found."
