#!/usr/bin/perl

use utf8;
#use Text::Unidecode;

open($file, "<$ARGV[0]");
open($outfile, ">$ARGV[1]");
while ($line=<$file>) {

    $line =~ s/^[^\x09\x0A\x0D\x20-\x7E]+//; # remove unprintable chars from beginning of lines
    $line =~ s/[^\x09\x0A\x0D\x20-\x7E]+\t/\t/g; # remove unprintable chars from end of column
#    $line =~ s/[^\x09\x0A\x0D\x20-\x7E]+([\x0A\x0D\x20-\x7E])/ \1/g;
#    $line =~ s/[^\x09\x0A\x0D\x20-\x7E]+\n$/\n/g;
    # remove extra spaces from columns
    $line =~ s/ +\t/\t/g;
    $line =~ s/ +\n/\n/g;
    $line =~ s/ +\"\t/\"\t/g;
    $line =~ s/ +\"\n/\"\n/g;
    #print $outfile unidecode($line);
    print $outfile $line;
}
close($file);
close($outfile);
