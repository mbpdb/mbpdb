#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: Oct 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu

use strict;

my %pepmods;
$pepmods{"+80"} = "P";
$pepmods{"+16"} = "O";
$pepmods{"+1"} = "D";
$pepmods{"-17"} = "G";
$pepmods{"-18"} = "DH";
$pepmods{"+58"} = "Ac";
$pepmods{"+42"} = "Ac";

my @mod_order = ("+80","+16","+1","-17","-18","+58","+42");

my ($fn, $xml_file, $label, $start, $end, $seq);
my %xml;

foreach $fn (@ARGV[2 .. $#ARGV]) {

#print STDERR "Reading file: $fn\n";
open ($xml_file, "<$fn");
while (<$xml_file>) {
    chomp;

    if ($_ =~ /<protein .+label=\"(.+?) .+\" / || $_ =~ /<protein .+label=\"(.+?)\" /) {
        $label = $1;
    }

    elsif ($_ =~ /<domain .+start=\"(\d+)\" end=\"(\d+)\" .+seq=\"(.+?)\" /) {
        $start = $1;
        $end = $2;
        $seq = $3;

        # make sure each label only gets added once
        $xml{$seq}{"label"} .= $label . " " if index($xml{$seq}{"label"},$label) == -1;
        $xml{$seq}{"start"} = $start;
        $xml{$seq}{"end"} = $end;
    }
}
close($xml_file);

}

my ($tsv_file, $header, $outfile);
my @data;
my @allmods;
my ($tempstr,$i,$peptide,$pepmodseq,$firstmod,$mod,$modn,$modnum);
my $linenum=2;
my $prevpep="";
my $prevpms="";
my @datatotal;
my @datanum;
my ($i,$j);

# convert input using dos2unix
system ("dos2unix -q \"$ARGV[0]\"");

open ($tsv_file, "<$ARGV[0]");
$header = <$tsv_file>;
chomp $header;
open ($outfile, ">$ARGV[1]");

my @hs = split(/\t/, $header);
$tempstr = join("\t", @hs[0 .. 6]);
for ($i=7; $i<=14; $i++) {
	for ($j=$i; $j < scalar(@hs); $j+=8) {
		$tempstr .= "\t" . $hs[$j]
	}
}

print $outfile "$tempstr\tPeptide start\tPeptide end\tModifications\n";

while (<$tsv_file>) {
    chomp;

    @data = split (/\t/);
    $peptide = $data[1];
    $pepmodseq = $data[5];

    # print if current peptide and modseq is different from previous
    if ($prevpep ne "" && ($peptide ne $prevpep || $pepmodseq ne $prevpms) && exists $xml{$prevpep}{"label"}) {

        # calculate averages
        for ($i=7; $i<=$#data; $i+=8) {
            $datatotal[$i+4] = $datatotal[$i+4] / $datanum[$i+4] if $datanum[$i+4] != 0;
            $datatotal[$i+6] = $datatotal[$i+6] / $datanum[$i+6] if $datanum[$i+6] != 0;
        }

	# rearranging columns
	$tempstr = join("\t",map {$_ eq "" ? "#N/A" : $_} @datatotal[1 .. 6]);
	for ($i=7; $i<=14; $i++) {
		for ($j=$i; $j < scalar(@datatotal); $j+=8) {
			$tempstr .= "\t" . ($datatotal[$j] ne "#N/A" ? $datatotal[$j] : "");
		}
	}

        $tempstr =~ s/ \t/\t/g;
        print $outfile $xml{$prevpep}{"label"} . "\t" . $tempstr . "\t" . $xml{$prevpep}{"start"} ."\t". $xml{$prevpep}{"end"} . "\t";

        if (@allmods = $prevpms =~ /\[([\-\+]\d+)\]/g) {

            foreach $mod (@allmods) {
                if (!exists $pepmods{$mod}) {
                    print STDERR "***Error: Modification $mod not defined with peptide $prevpep on line ".($linenum-1)." of TSV file. Aborting.\n";
                    close($outfile);
                    unlink($ARGV[1]);
                    exit(1);
                }
            }

            $firstmod=1;
            foreach $mod (@mod_order) {

                $modn = $mod;
                $modn =~ s/\+/\\\+/;
                $modn =~ s/\-/\\\-/;
                $modnum = () = $prevpms =~ /(\[$modn\])/g;

                if ($modnum != 0) {
                    if ($firstmod) {$firstmod=0;}
                    else {print $outfile " ";}

                    print $outfile $modnum . $pepmods{$mod};
                }
            } 
        }

        else {print $outfile " ";}

        print $outfile "\n";

        @datatotal = ();
        @datanum = ();
    }

    elsif ($prevpep ne "" && !exists $xml{$prevpep}{"label"}) {
        print STDERR "***Error: Peptide $prevpep (on line ".($linenum-1)." of TSV file) not found in XML. Aborting.\n";
        close($outfile);
        unlink($ARGV[1]);
        exit(1);
    }


    #accumulate data
    $datatotal[1] = $data[1]; # peptide
    $datatotal[2] .= $data[2] . " " if $data[2] ne "#N/A"; # precursor
    $datatotal[3] .= $data[3] . " " if $data[3] ne "#N/A"; # precursor charge
    $datatotal[4] .= $data[4] . " " if $data[4] ne "#N/A"; # precursor Mz
    $datatotal[5] = $data[5]; # peptide modified sequence
    $datatotal[6] = $data[6]; # library name

    for ($i=7; $i<=$#data; $i+=8) {
        $datatotal[$i] .= $data[$i] . " " if $data[$i] ne "#N/A"; # best retention time
        $datatotal[$i+1] = $data[$i+1]; # min start time
        $datatotal[$i+2] = $data[$i+2]; # max end time
        $datatotal[$i+3] += $data[$i+3] if $data[$i+3] ne "#N/A"; # total area
        $datatotal[$i+4] += $data[$i+4] if $data[$i+4] ne "#N/A"; # average mass error PPM
        $datanum[$i+4]++ if $data[$i+4] ne "#N/A";
        $datatotal[$i+5] = $data[$i+5]; # file name
        $datatotal[$i+6] += $data[$i+6] if $data[$i+6] ne "#N/A"; # isotope dot product
        $datanum[$i+6]++ if $data[$i+6] ne "#N/A";
        $datatotal[$i+7] = $data[$i+7]; # identified
    }

    $linenum++;
    $prevpep = $peptide;
    $prevpms = $pepmodseq;
}


# do last peptide
    if (exists $xml{$prevpep}{"label"}) {
        $tempstr = join("\t",map {$_ eq "" ? "#N/A" : $_} @datatotal[1 .. 6]);
	for ($i=7; $i<=14; $i++) {
                for ($j=$i; $j < scalar(@datatotal); $j+=8) {
                        $tempstr .= "\t" . ($datatotal[$j] ne "#N/A" ? $datatotal[$j] : "");
                }
        }

        $tempstr =~ s/ \t/\t/g;
        print $outfile $xml{$prevpep}{"label"} . "\t" . $tempstr . "\t" . $xml{$prevpep}{"start"} ."\t". $xml{$prevpep}{"end"}."\t";


        if (@allmods = $prevpms =~ /\[([\-\+]\d+)\]/g) {

            foreach $mod (@allmods) {
                if (!exists $pepmods{$mod}) {
                    print STDERR "***Error: Modification $mod not defined with peptide $prevpep on line ".($linenum-1)." of TSV file. Aborting.\n";
                    close($outfile);
                    unlink($ARGV[1]);
                    exit(1);
                }
            }

            $firstmod=1;
            foreach $mod (@mod_order) {

                $modn = $mod;
                $modn =~ s/\+/\\\+/;
                $modn =~ s/\-/\\\-/;
                $modnum = () = $prevpms =~ /(\[$modn\])/g;

                if ($modnum != 0) {
                    if ($firstmod) {$firstmod=0;}
                    else {print $outfile " ";}

                    print $outfile $modnum . $pepmods{$mod};
                }
            }
        }

	else {print $outfile " ";}

        print $outfile "\n";
    }

    else {
        print STDERR "***Error: Peptide $prevpep (on line ".($linenum-1)." of TSV file) not found in XML. Aborting.\n";
        close($outfile);
        unlink($ARGV[1]);
        exit(1);
    }



close ($outfile);
close ($tsv_file);

