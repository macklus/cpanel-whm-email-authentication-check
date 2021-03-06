#!/usr/local/cpanel/3rdparty/bin/perl
# Copyright 2017 Jose Pedro Andres
# URL: https://github.com/macklus/cpanel-whm-mail-outgoing-ips
# Email: macklus@debianitas.net

use Cpanel::Form            ();
use Whostmgr::ACLS          ();
use Cpanel::SafeFile        ();
use Cpanel::Rlimit          ();
use Cpanel::PublicAPI       (); 
use IPC::Open3;
use Data::Dumper;
use List::Util qw(any);


#use Sys::Hostname qw(hostname);
#use IPC::Open3;
#use File::Basename;
#use lib '/usr/local/cpanel';
#use Cpanel::cPanelFunctions ();
#use Cpanel::Config          ();
#use Cpanel::Version::Tiny   ();

my $api = new Cpanel::PublicAPI(usessl => 0, user => 'root', accesshash => _read_hash());
my %resellers;
my @excludedomains;
my @localdomains;
my $changes = 0;

my %FORM = Cpanel::Form::parseform();

print "Content-type: text/html\r\n\r\n";

Whostmgr::ACLS::init_acls();
if (!Whostmgr::ACLS::hasroot()) {
    print "You do not have access to this option.\n";
#    exit();
}

Cpanel::Rlimit::set_rlimit_to_infinity();

do_head();

#print Dumper(%FORM);

#
# Get current resellers and their config
#

if( $FORM{'action'} eq 'save_config' ) {
	$changes = update_resellers_config(%FORM);
	$changes = $changes + update_exclude_domains(%FORM);
}

%resellers = get_reseller_data();
@localdomains = get_local_domains();
@excludedomains = get_excluded_domains();

print '<h2>Mail Authentication Check</h2>';
print '<p class="bg-success success-msg">Changes sucesfully commited</p>' if( $changes > 0);

print <<'DO_TABS';
<br>
<ul class="nav nav-tabs" role="tablist">
	<li role="presentation" class="active"><a href="#config" aria-controls="config" role="tab" data-toggle="tab">Configuration</a></li>
	<li role="presentation"><a href="cmac-check.cgi?action=check" role="tab" >Check!</a></li>
</ul>
DO_TABS

print '<div class="tab-content">';
print '<div role="tabpanel" class="tab-pane active" id="config">';
print <<'DO_RESELLER_TABLE_HEAD';

<br>
<p>Use this form to define how domains should be configured according to their reseller.</p>
<br>
<form method="post" action="">
<table class="table table-striped table-bordered">
<thead>
<tr>
	<th class="text-center">Reseller</th><th class="text-center">DNS 1</th><th class="text-center">DNS 2</th><th class="text-center">DNS 3</th><th class="text-center">SPF</th><th class="text-center">DMARC</th>
</tr>
</thead>
<tbody>
DO_RESELLER_TABLE_HEAD
foreach my $rk( keys %resellers) {
	if( $rk =~ /\w+/ && $rk !~ /HASH\(/ ) {
		print <<"DO_RESELLER_TABLE_TR";

<tr>
	<td>$rk</td>
	<td class='text-center'><input type='text' class='form-control' name='${rk}_ns1' value='$resellers{$rk}{'ns1'}'></td>
	<td class='text-center'><input type='text' class='form-control' name='${rk}_ns2' value='$resellers{$rk}{'ns2'}'></td>
	<td class='text-center'><input type='text' class='form-control' name='${rk}_ns3' value='$resellers{$rk}{'ns3'}'></td>
	<td class='text-center'><input type='text' class='form-control' name='${rk}_spf' value='$resellers{$rk}{'spf'}'></td>
	<td class='text-center'><input type='text' class='form-control' name='${rk}_dmarc' value='$resellers{$rk}{'dmarc'}'></td>
</tr>

DO_RESELLER_TABLE_TR
	}
}

print '</tbody>';
print '</table>';
print <<'DO_EXCLUDE_DOMAINS_TABLE_HEAD';
<h3>Exclude domains or subdomains</h3>
<table class="table table-striped table-bordered">
<tbody>

DO_EXCLUDE_DOMAINS_TABLE_HEAD
my $ld_count = 0;
foreach my $ld ( @localdomains ) {
	print '<tr>' if($ld_count == 0 );

	my $is_excluded = 0;
	foreach my $ed ( @excludedomains ) {
		chomp $ed;
		if( $ed eq $ld ) {
			$is_excluded = 1;
		}
	}

	print "<td><input type='checkbox' name='exclude_$ld' " . ( $is_excluded == 1 ? 'checked' : "" ) . ">&nbsp;$ld</td>";

	$ld_count++;
	
	if($ld_count == 4 ) {
		print '</tr>';
		$ld_count=0;

	}

}


print '</tbody>';
print '</table>';

print '<input type="hidden" name="action" value="save_config">';
print '<input type="submit" class="btn btn-primary" value="Send">';
print '</form>';


#print '<div role="tabpanel" class="tab-pane" id="check">...</div>';
#print '</div>';

end_head();
#
# Works end
#

sub update_exclude_domains() {
	my %FORM = @_;
    @exclude = ();
    foreach(keys %FORM) {
        if($_ =~ /exclude_(.*)/) {
            push(@exclude, $1);
        }
    }
	my $outlock = Cpanel::SafeFile::safeopen(\*OUT,">","/etc/cpanel-whm-mail-authentication-check-excludes");
    foreach( @exclude ) {
        print OUT "$_\n";
    }
    Cpanel::SafeFile::safeclose(\*OUT,$outlock);

    return 1;
}

sub get_local_domains() {
    my @d;
    my $inlock = Cpanel::SafeFile::safeopen(\*IN,"<","/etc/userdatadomains");
    my @data = <IN>;
    Cpanel::SafeFile::safeclose(\*IN,$inlock);
    foreach( @data ) {
        chomp;
        if( /(.*): (.*)==(.*)==(.*)==(.*)==(.*)==(.*)==(.*)==(.*)==0/ ) {
			next if( $4 eq 'sub' );
			push(@d, $1 );
        }
    }
    return @d;
}

sub get_excluded_domains() {
	my @res;
	open(CE, "</etc/cpanel-whm-mail-authentication-check-excludes" ) or return @res;
	while (my $line = <CE> ) {
		chop $line;
		push(@res, $line);
	}
	close( CE );
	return @res;
}
sub update_resellers_config(%FORM) {
	my $FORM = @_;
	my %result;
	my %udd = get_userdatadomains();
    foreach my $u ( keys %udd ) {
        my $r = $udd{$u}{'reseller'};
		next if( $r eq '' );
        $result{$r} = ();
    }

	foreach( keys %result ) {
		$result{$_}[0] = $_;
		$result{$_}[1] = $FORM{${_}."_ns1"};
		$result{$_}[2] = $FORM{${_}."_ns2"};
		$result{$_}[3] = $FORM{${_}."_ns3"};
		$result{$_}[4] = $FORM{${_}."_spf"};
		$result{$_}[5] = $FORM{${_}."_dmarc"};
	}

	my $outlock = Cpanel::SafeFile::safeopen(\*OUT,">","/etc/cpanel-whm-mail-authentication-check");
   	foreach( keys %result ) {
		print OUT join('|', @{$result{$_}} )."\n";
	} 
	Cpanel::SafeFile::safeclose(\*OUT,$outlock);

	return 1;
}

sub get_reseller_data() {
	my %result = {};
	my %udd = get_userdatadomains();
	foreach my $u ( keys %udd ) {
		my $r = $udd{$u}{'reseller'};		
		$result{$r} = '';
	}

    my %d = {};
    my $inlock = Cpanel::SafeFile::safeopen(\*IN,"<","/etc/cpanel-whm-mail-authentication-check");
    my @data = <IN>;
    Cpanel::SafeFile::safeclose(\*IN,$inlock);
    foreach( @data ) {
        chomp;
		my @pos = split(/\|/, $_ );
		if( defined($result{$pos[0]}) ) {
			$result{$pos[0]}{'ns1'} = $pos[1];
			$result{$pos[0]}{'ns2'} = $pos[2];
			$result{$pos[0]}{'ns3'} = $pos[3];
			$result{$pos[0]}{'spf'} = $pos[4];
			$result{$pos[0]}{'dmarc'} = $pos[5];
		}
    }

	return %result;
}


sub _read_hash() {
    my $AccessHash = "/root/.accesshash";

    eval {
        unless ( -f $AccessHash )
        {
            my $pid = IPC::Open3::open3( my $wh, my $rh, my $eh,
                '/usr/local/cpanel/whostmgr/bin/whostmgr setrhash' );
            waitpid( $pid, 0 );
        }
    };
    open( my $hash_fh, "<", $AccessHash ) || die "Cannot open access hash: " . $AccessHash;

    my $accesshash = do { local $/; <$hash_fh>; };
    $accesshash =~ s/\n//g;
    close($hash_fh);

    return $accesshash;
}

sub get_hash_for_file {
    my $file = shift;
    my %d = ();    
    if ( -e $file ) {
        my $inlock = Cpanel::SafeFile::safeopen(\*IN,"<","$file");
        my @data = <IN>;
        Cpanel::SafeFile::safeclose(\*IN,$inlock);

        foreach( @data ) {
            chomp;
            if( /(.*): (.*)/ ) {
                $d{$1} = $2;
            }
        }
    }
    return %d;
}

sub get_userdatadomains {
    my %d = {};
    my $inlock = Cpanel::SafeFile::safeopen(\*IN,"<","/etc/userdatadomains");
    my @data = <IN>;
    Cpanel::SafeFile::safeclose(\*IN,$inlock);
    foreach( @data ) {
        chomp;
        if( /(.*): (.*)==(.*)==(.*)==(.*)==(.*)==(.*)==(.*)==(.*)==0/ ) {
            $d{$1}{'domain'} = $1;
            $d{$1}{'user'} = $2;
            $d{$1}{'reseller'} = $3;
            $d{$1}{'type'} = $4;
            $d{$1}{'main_domain'} = $5;
            $d{$1}{'home'} = $6;
            $d{$1}{'ip_hosts'} = $7;
        }
    }
    return %d;
}

sub do_head {
 print <<'DO_HEADER';
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Exim Outgoing IP config</title>
    <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.6/css/bootstrap.min.css" crossorigin="anonymous">
	<script src="https://code.jquery.com/jquery-3.1.0.min.js" crossorigin="anonymous"></script>
	<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js" crossorigin="anonymous"></script>
    <style type="text/css">
    .success-msg {
        padding: 30px;
        marging: 30px;
    }
    </style>
</head>
<body>
    <div class="container">
DO_HEADER
}

sub end_head {
    print <<'END_HEADER';
    </div> <!-- /container -->
</body>
</html>
END_HEADER
}

1;
