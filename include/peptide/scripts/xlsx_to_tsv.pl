#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: April 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu


my $firstcol=1;
my $usefirstsheet=1;

#use Text::Iconv;
#my $converter = Text::Iconv -> new ("utf-8", "windows-1251");
 
# Text::Iconv is not really required.
# This can be any object with the convert method. Or nothing.
 
use Spreadsheet::XLSX;
 
#my $excel = Spreadsheet::XLSX -> new ($ARGV[0], $converter);
my $excel = Spreadsheet::XLSX -> new ($ARGV[0]);

open ($outfile, ">$ARGV[1]");
 
foreach my $sheet (@{$excel -> {Worksheet}}) {
        if ($usefirstsheet) {$usefirstsheet=0;}
        else {next;}
 
#       printf("Sheet: %s\n", $sheet->{Name});
        
       $sheet -> {MaxRow} ||= $sheet -> {MinRow};
        
        foreach my $row ($sheet -> {MinRow} .. $sheet -> {MaxRow}) {
         
               $sheet -> {MaxCol} ||= $sheet -> {MinCol};
                
               foreach my $col ($sheet -> {MinCol} ..  $sheet -> {MaxCol}) {
                
                       my $cell = $sheet -> {Cells} [$row] [$col];
                        if ($firstcol) {$firstcol=0;}
                        else {print $outfile "\t";}
 
                       if ($cell) {
                           # printf("( %s , %s ) => %s\n", $row, $col, $cell -> {Val});
                            $cell_contents = $cell -> {Val};
                            $cell_contents =~ s/\&gt\;/>/g;
                            $cell_contents =~ s/\&apos\;/\'/g;
                            print $outfile $cell_contents;
                       }
 
               }

                print $outfile "\n";
                $firstcol=1;
 
       }
 
}

close ($outfile);
