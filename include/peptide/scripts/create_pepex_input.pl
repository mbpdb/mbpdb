#!/usr/bin/perl

$input_tsv = $ARGV[0];
$outfile = $ARGV[1];

open ($out, ">$outfile");
print $out "Name,Volumen,Notes,Sample,Phospho\n";

open ($input, "<$input_tsv");
$header = <$input>;
chomp $header;
close($input);

@hdata = split(/\t/, $header);
$numsamps = ($#hdata - 9) / 8;

# iterate through Total Area column headers
for ($i=($numsamps*3)+10; $i<=($numsamps*4)+9; $i++) {

    open ($input, "<$input_tsv");
    <$input>; # header

    while ($line=<$input>) {
        chomp $line;

        @data = split(/\t/, $line);
        print $out "$data[1],".($data[$i] eq "" ? "0" : $data[$i]).",$data[0],$hdata[$i],$data[8]\n";
    }

    close ($input);
}

close ($out);
