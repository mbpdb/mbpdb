#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: Oct 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu


system ("dos2unix \"$ARGV[0]\"");

open ($tsv, "<$ARGV[0]");
open ($outfile, ">$ARGV[1]");

$IDOTP_THRESHOLD = $ARGV[2];
$ONLY_KEEP_TRUE = $ARGV[3];

$header = <$tsv>;
print $outfile $header;

while (<$tsv>) {
	chomp;
	@data = split (/\t/);

	print $outfile join ("\t", @data[0 .. 6]);

	for ($i=7; $i < scalar(@data); $i+=8) {
		if ($data[$i+7] eq "FALSE") {
			print $outfile "\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A";
			#print $outfile "\t\t\t\t\t\t\t\t";
		}

		elsif ($data[$i+7] eq "ALIGNED" && ($data[$i+6] <= $IDOTP_THRESHOLD || $ONLY_KEEP_TRUE)) {
			print $outfile "\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A\t#N/A";
			#print $outfile "\t\t\t\t\t\t\t\t";
		}

		else {
			print $outfile "\t" . join ("\t", @data[$i .. $i+7]);
		}
	}

	print $outfile "\n";
}

close($tsv);
close($outfile);
