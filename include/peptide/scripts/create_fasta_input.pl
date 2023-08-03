#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: April 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu


open ($finput, "<$ARGV[0]");
open ($foutput, ">$ARGV[1]");
open ($fasta, ">$ARGV[2]");

$num=1;

while (<$finput>) {
	chomp;

	if ($_=~/^Protein/) {
		print $foutput "ID\t$_\n";
		next;
	}

    @data = split (/\t/);
	
	print $foutput "INPUT$num\t$_\n";
	print $fasta ">INPUT$num\n$data[1]\n";
	$num++;
}

close($finput);
close($foutput);
close($fasta);
