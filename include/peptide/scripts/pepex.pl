#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: February 2016
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu

opendir($dh,$ARGV[0]);
@fasta_files = grep {-f "$ARGV[0]/$_"} readdir($dh);
closedir($dh);

$only_count_pep = $ARGV[3];

# read in fasta data
foreach $file (@fasta_files) {

    # print STDERR "Reading file $file...\n";

    open ($fd, "<$ARGV[0]/$file");
    while (<$fd>) {
        chomp;

        if ($_ =~ /^>(.+?) (.+)$/) {
            $header = $1;
            $fdesc{$header} = $2;
            next;
        }

        $fseq{$header} .= $_;
    }
    close ($fd);
}


open ($skyline, "<$ARGV[1]");
$header = <$skyline>;
chomp $header;

@hdata = split(/\t/, $header);

if ($hdata[10] =~ /Total Area/) {
    $numsamps = $#hdata - 9;
    $tot_area_begin = 10;
    $tot_area_end = $numsamps + 9;
} else {
    $numsamps = ($#hdata - 9) / 8;
    $tot_area_begin = ($numsamps*3)+10;
    $tot_area_end = ($numsamps*4)+9;
}
# print STDERR "Numsamps: $numsamps\n";

while (<$skyline>) {
    chomp;

    @data = split (/\t/);
    $proteins = $data[0];
    $start = $data[6]-1; # for zero-based indexing
    $end = $data[7]-1;

    # for protein fields that have more than one ID
    foreach $protein (split(/ /,$proteins)) {

    if (!exists $fseq{$protein}) {
        if (!exists $errors{$protein}) {
            print STDERR "Protein '$protein' not found in fasta files.\n";
        }
        $errors{$protein}=1;
        next;
    }

    #print STDERR "Using protein $protein\n";

    # sum up total area columns per protein, per AA, per sample
    for ($i=$start; $i<=$end; $i++) { # AA index
        if (!exists $total{$protein}{$i}) {$total{$protein}{$i}=0;}

        for ($j=$tot_area_begin; $j<=$tot_area_end; $j++) { # sample total area index
            if (!exists $counts{$protein}{$i}{$j}) {$counts{$protein}{$i}{$j}=0;}

            # either count values or sum them up
            $addval = ($only_count_pep == 1 ? 1 : $data[$j]);

            # sum up total area columns
            $counts{$protein}{$i}{$j} += ($data[$j] eq "" ? 0 : $addval);
            $total{$protein}{$i} += ($data[$j] eq "" ? 0 : $addval);
        }
    }

    }
}

close($skyline);


open ($outfile, ">$ARGV[2]");
foreach $protein (sort keys %counts) {

    if (exists $fseq{$protein}) {

        # print out header for each protein
        print $outfile "$protein\n$fdesc{$protein}\nAA Index,AA,Total Volume";
        for ($j=$tot_area_begin; $j<=$tot_area_end; $j++) {
            print $outfile ",$hdata[$j]";
        }
        print $outfile "\n";

        # print out sums per amino acid
        @aa = split(//, $fseq{$protein});
        for ($i=0; $i<=$#aa; $i++) {
            print $outfile "".($i+1).",$aa[$i],".(exists $total{$protein}{$i} ? $total{$protein}{$i} : 0);

            for ($j=$tot_area_begin; $j<=$tot_area_end; $j++) {
                print $outfile ",".(exists $counts{$protein}{$i}{$j} ? $counts{$protein}{$i}{$j} : 0);
            }

            print $outfile "\n";
        }
    }

    print $outfile "\n\n";
}
close($outfile);
