#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: Oct 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu

$remove_all_mods = $ARGV[0];

foreach $xmlfile (@ARGV[1 .. $#ARGV]) {

$outfile = $xmlfile;
$outfile =~ s/\.xtan\.xml$/.domains_removed.xtan.xml/i;
open ($out, ">$outfile");

$domain = "";

open ($xml, "<$xmlfile");
while ($line=<$xml>) {

    if ($line =~ /^<domain id=\"(.+?)\"/) {
        $domain = $1;
        if ($domain =~ /.+\.1\.1/) {
            print $out $line;
        }
    }

    elsif ($line =~ /^<aa type=/) {
        if ($domain =~ /.+\.1\.1/) {
            print $out $line if $remove_all_mods == 0;
        }
    }

    elsif ($line =~ /^<\/domain>/) {
        if ($domain =~ /.+\.1\.1/) {
            print $out $line;
        }
    }

    else {
        print $out $line;
    }
}

close ($xml);
close ($out);

}
