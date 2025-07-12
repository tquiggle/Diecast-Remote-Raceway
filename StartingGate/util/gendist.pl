#! /usr/bin/perl

# Script to create distribution file from current directory contents.
# In Perl, just because.

use strict;

my $dist_dir = "/home/htdocs/DRR/SG";  # Directory where SG distribution files are located
my $ver = 0;                            # distribution version from within a single day

# Check for existing distributions from today
my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) = localtime();
$year -= 100;
$mon += 1;

my $pattern = sprintf("$dist_dir/starting-gate-%2d%02d%02d", $year, $mon, $mday);

my @today_builds = `ls $pattern*`;
if ($#today_builds >= 0) {
    my $last = @today_builds[-1];
    if ($last =~ /(\d\d).tgz/) {
        $ver = $1;
        $ver++;
    } else {
        print "Distribution file '$last' does not match file pattern\n";
        exit -1;
    }
}

my $version = sprintf("%2d%02d%02d%02d", $year, $mon, $mday, $ver);
my $dist_filename = sprintf("$dist_dir/starting-gate-%s.tgz", $version);

open VER, "> version.txt" || die "Unable to write version file\n";
print VER "$version\n";
close VER;

print "Creating distribution file $dist_filename\n";

system("tar cz --exclude='__pycache__' --exclude='dist' --exclude='STL' --exclude='releases' --exclude='config/starting_gate.json' -f $dist_filename *");

system("cp version.txt $dist_dir/")

