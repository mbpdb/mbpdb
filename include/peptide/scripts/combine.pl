#!/usr/bin/perl

# AUTHOR: Nikhil Joshi <najoshi@ucdavis.edu>
# LAST REVISED: August 2015
# The Bioinformatics Core at UC Davis Genome Center
# http://bioinformatics.ucdavis.edu


open($pepinput, "<$ARGV[0]");
open($funclib, "<$ARGV[1]");

$header=<$pepinput>;
chomp $header;
while ($line=<$pepinput>) {
    chomp $line;
    @data=split (/\t/, $line);

    $pep{$data[0]}{"seq"} = $data[2];
    $pep{$data[0]}{"vols"} = join("\t", @data[2 .. $#data]);

# print "$data[0]: " . $pep{$data[0]}{"seq"} . "\n";
}

<$funclib>;
while ($line=<$funclib>) {
    chomp $line;
    @data=split (/\t/, $line);

    $func{$data[0]}{"pepname"} = $data[2];
    $func{$data[0]}{"prot"} = $data[3];
    $func{$data[0]}{"species"} = $data[4];
    $func{$data[0]}{"seq"} = $data[6];
    $func{$data[0]}{"posstart"} = $data[8];
    $func{$data[0]}{"posend"} = $data[9];
    $func{$data[0]}{"pos"} = $data[10];
    $func{$data[0]}{"func"} = $data[13];
    $func{$data[0]}{"ref"} = $data[14];
}

close($pepinput);
close($funclib);


open($blastout, "<$ARGV[2]");
open($homout, ">$ARGV[3]");

($sampids)=$header=~/^ID\tProtein\t(.+)/;
# print $homout "Matched library peptide name/ref number\tmatched library protein of origin\tmatched library species\tmatched library sequence\tmatched library position start (counting signal sequence)\tmatched library position end (counting signal sequence)\tMatched library position (not counting signal seq)\tMatched lib reference\tData pep seq\t% match\tL30MS\tL31MS\tL32MS\tL33MS\tL34MS\tL35MS\tL36Rerun\tL37MS\tL38MS\tL39MS\tL40MS\tL41MS\tL42MS\tL43MS\tL44MS\tL45MS\tL46MS\tL47MS\tL48MS\tL49MS\tL50Rerun\tL51Rerun\tL52Rerun\tL53Rerun\tL54Rerun\tL55Rerun\tL56MS\tL57MS\tL58MS\tL59MS\tL60MS\tjuneL10\tjuneL11\tjuneL12\tjuneL13\tjuneL14\tjuneL15\tjuneL16\tjuneL17\tjuneL18\tjuneL19\tjuneL1_2\tjuneL20Rerun\tjuneL21\tjuneL22\tjuneL23\tjuneL24\tjuneL25\tjuneL26\tjuneL27\tjuneL28\tjuneL29_2\tjuneL2_2\tjuneL3\tjuneL4\tjuneL5\tjuneL6\tjuneL7\tjuneL8\tjuneL9\n";
print $homout "Matched library peptide name/ref number\tmatched library protein of origin\tmatched library species\tmatched library sequence\tmatched library position start (counting signal sequence)\tmatched library position end (counting signal sequence)\tMatched library position (not counting signal seq)\tFunction\tMatched lib reference\tData pep seq\t% subject match\t% query match\t$sampids\n";

while ($line=<$blastout>) {
    chomp $line;
    @data=split (/\t/, $line);

    $qid = $data[0];
    $sid = $data[1];
    $matchlen = $data[3];
    $mismatches = $data[4];
    $qlen = $data[12];
    $slen = $data[13];
    $gaps = $data[14];

    $percent_match_s = 100 * (($matchlen - $gaps - $mismatches) / $slen);
    $percent_match_s = sprintf("%.1f", $percent_match_s);

    $percent_match_q = 100 * (($matchlen - $gaps - $mismatches) / $qlen);
    $percent_match_q = sprintf("%.1f", $percent_match_q);

    print $homout $func{$sid}{"pepname"} . "\t" . $func{$sid}{"prot"} . "\t" . $func{$sid}{"species"} . "\t" . $func{$sid}{"seq"} . "\t" . $func{$sid}{"posstart"} . "\t" . $func{$sid}{"posend"} . "\t" . $func{$sid}{"pos"} . "\t" . $func{$sid}{"func"} . "\t" . $func{$sid}{"ref"} . "\t" . $pep{$qid}{"seq"} . "\t$percent_match_s\t$percent_match_q\t" . $pep{$qid}{"vols"} . "\n";
    # print $homout $func{$sid}{"pepname"} . "\t" . $func{$sid}{"prot"} . "\t" . $func{$sid}{"species"} . "\t" . $func{$sid}{"seq"} . "\t" . $func{$sid}{"posstart"} . "\t" . $func{$sid}{"posend"} . "\t" . $func{$sid}{"pos"} . "\t" . $func{$sid}{"ref"} . "\t" . $pep{$qid}{"seq"} . "\t" . (100 * (($matchlen - $gaps) / $slen)) . "\n";
}

close($blastout);
close($homout);
