#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: Nov 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu

open ($tsv, "<$ARGV[0]");
open ($outfile, ">$ARGV[1]");

$prevpep = "";
$prevmod = "";
@datatotal = ();
@datanum = ();
$header=<$tsv>; # header
print $outfile $header;

print STDERR "header: '$header'\n";

while ($line = <$tsv>) {
	chomp $line;

	@data = split (/\t/, $line);
	$pep = $data[1];
	$mod = $data[$#data];

# print STDERR "pep: '$pep', prevpep: '$prevpep', mod: '$mod', prevmod: '$prevmod'\n";

    if ($prevpep ne "" && ($pep ne $prevpep || ($mod ne $prevmod && ($mod ne " " || $prevmod ne " ")))) {
        # calculate averages
        for ($i=7; $i<=$#data; $i+=8) {
            $datatotal[$i+4] = $datatotal[$i+4] / $datanum[$i+4] if $datanum[$i+4] != 0;
            $datatotal[$i+6] = $datatotal[$i+6] / $datanum[$i+6] if $datanum[$i+6] != 0;
        }

# print STDERR "printing...\n";

        print $outfile join("\t",@datatotal) . "\n";

        @datatotal = ();
        @datanum = ();
    }

		#accumulate data
            	$datatotal[0] = $data[0]; # protein
    		$datatotal[1] = $data[1]; # peptide
    		$datatotal[2] .= $data[2] . " " if $data[2] ne ""; # precursor
    		$datatotal[3] .= $data[3] . " " if $data[3] ne ""; # precursor charge
    		$datatotal[4] .= $data[4] . " " if $data[4] ne ""; # precursor Mz
    		$datatotal[5] .= $data[5] . " "; # peptide modified sequence
    		$datatotal[6] = $data[6]; # library name

    		for ($i=7; $i<=$#data-3; $i+=8) {
        		$datatotal[$i] .= $data[$i] . " " if $data[$i] ne ""; # best retention time
        		$datatotal[$i+1] = $data[$i+1]; # min start time
        		$datatotal[$i+2] = $data[$i+2]; # max end time
        		$datatotal[$i+3] += $data[$i+3] if $data[$i+3] ne ""; # total area
        		$datatotal[$i+4] += $data[$i+4] if $data[$i+4] ne ""; # average mass error PPM
        		$datanum[$i+4]++ if $data[$i+4] ne "";
        		$datatotal[$i+5] = $data[$i+5]; # file name
        		$datatotal[$i+6] += $data[$i+6] if $data[$i+6] ne ""; # isotope dot product
        		$datanum[$i+6]++ if $data[$i+6] ne "";
        		$datatotal[$i+7] = $data[$i+7]; # identified
    		}

		$datatotal[$#data-2] = $data[$#data-2]; # peptide start
		$datatotal[$#data-1] = $data[$#data-1]; # peptide end
		$datatotal[$#data] = $data[$#data]; # modifications

	$prevpep = $pep;
	$prevmod = $mod;
}


# last line
    # calculate averages
    for ($i=7; $i<=$#data; $i+=8) {
        $datatotal[$i+4] = $datatotal[$i+4] / $datanum[$i+4] if $datanum[$i+4] != 0;
        $datatotal[$i+6] = $datatotal[$i+6] / $datanum[$i+6] if $datanum[$i+6] != 0;
    }

    print $outfile join("\t",@datatotal) . "\n";


close ($tsv);
close ($outfile);
