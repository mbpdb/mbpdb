#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: Oct 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu

open ($tsv, "<$ARGV[0]");
open ($outfile, ">$ARGV[1]");
$reduce_columns = $ARGV[2];

while (<$tsv>) {
	chomp;

	@data = split (/\t/);

	# output all columns with last three rearranged
	if (!$reduce_columns) {
		print $outfile join ("\t", @data[0 .. 5]) . "\t" . join ("\t", @data[$#data-2 .. $#data]) . "\t" . join ("\t", @data[6 .. $#data-3]) . "\n";
	}

	# output only Total Area columns for samples, and last three rearranged
	else {
		$numsamps = ($#data - 9) / 8;
		print $outfile join ("\t", @data[0 .. 5]) . "\t" . join ("\t", @data[$#data-2 .. $#data]) . "\t$data[6]\t" . join("\t", @data[($numsamps*3)+7 .. ($numsamps*4)+6]) . "\n";
	}
}

close($tsv);
close($outfile);
