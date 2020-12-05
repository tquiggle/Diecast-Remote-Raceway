#! /usr/bin/perl

# Script to update distribution directory with current build
# In Perl, just because.

use strict;

my $dist_dir = "/home/htdocs/DRR/FL";  # Directory where FL distribution files are located
my $ver = "";                          # distribution version from within a single day

my $src_file = "finishline/finishline.ino";
my $bin_file = "finishline/finishline.ino.esp32.bin";

my $src_mtime = (stat($src_file))[9];
my $bin_mtime = (stat($bin_file))[9];

die "Source file is newer than binary. Please recompile." if ($src_mtime > $bin_mtime);

# Get distribution string from source
open my $fh, "< $src_file" || die "Unable to open source";
while (<$fh>) {
    if (/FW_VERSION\s*=\s*"(\d+)"/) {
        $ver = $1;
        last;
    }
}
close $fh;

die "Unable to determine source version" if ($ver == "");

my $dist_filename = sprintf("$dist_dir/finish-line-%s.bin", $ver);
print "Releasing $bin_file to $dist_filename\n";
system("cp $bin_file $dist_filename");
open $fh, "> $dist_dir/version.txt";
print $fh "$ver\n";
close $fh;

