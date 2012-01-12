#!/usr/bin/env perl

# Print the docs if no arguments are supplied.

print_docs();

# Set our environment variables.

if ($ENV{'NOVA_API_KEY'}) {
	$NOVA_API_KEY = $ENV{'NOVA_API_KEY'};
} else {
	die "NOVA_API_KEY environment variable must be set.";
};

if ($ENV{'NOVA_USERNAME'}) {
	$NOVA_USERNAME = $ENV{'NOVA_USERNAME'};
} else {
	die "NOVA_USERNAME environment variable must be set.";
};

if ($ENV{'NOVA_PROJECT_ID'}) {
	$NOVA_PROJECT_ID = $ENV{'NOVA_PROJECT_ID'};
	$nova_project = "-H \"X-Auth-Project-Id: $NOVA_PROJECT_ID\"";
};

if ($ENV{'NOVA_URL'}) {
	$NOVA_URL = $ENV{'NOVA_URL'};
} else {
	die "NOVA_URL environment variable must be set.";
};

# First, get our auth info.
$auth = `curl -s -D - -H "X-Auth-Key: $NOVA_API_KEY" -H "X-Auth-User: $NOVA_USERNAME" "$NOVA_URL" 2>&1`;

if ($auth =~ /X-Auth-Token: ([^\n]*)/) {
	$token = $1;
	$token =~ s/[^a-zA-Z0-9\-\_]//g;
} else {
	die "Error: No Auth Token returned.\nDetails:\n$auth";
};

if ($auth =~ /X-Server-Management-Url: ([^\n\r]*)/) {
	$mgturl = $1;
} else {
	die "Error: No Server Management Url returned.\nDetails:\n$auth";
};

foreach $arg (@ARGV) {
	if ($arg eq "-p") {
		$pretty = 1;
	} elsif (!($url)) {
		$url = $arg;
	} else {
		$post = $arg;
	};
};

if ($post) {

# If we have a second argument, it's a POST value.

	if ($pretty) {
		$resp = `curl -s -H "X-Auth-Token: $token" $nova_project -H "X-Auth-User: $NOVA_USERNAME" -H "Content-type: application/json" -d '$post' "$mgturl$url" 2>&1 | python -mjson.tool`;
	} else {
		$resp = `curl -s -H "X-Auth-Token: $token" $nova_project -H "X-Auth-User: $NOVA_USERNAME" -H "Content-type: application/json" -d '$post' "$mgturl$url" 2>&1`;
	};

} else {

# No second argument, it's a GET.

	if ($pretty) {
		$resp = `curl -s -H "X-Auth-Token: $token" $nova_project -H "X-Auth-User: $NOVA_USERNAME" "$mgturl$url" 2>&1 | python -mjson.tool`;
	} else {
		$resp = `curl -s -H "X-Auth-Token: $token" $nova_project -H "X-Auth-User: $NOVA_USERNAME" "$mgturl$url" 2>&1`;
	};
};

chomp $resp;
print $resp."\n";

sub print_docs {
	if (!($ARGV[0])) {
		print <<EOT;
nova_query.pl suburl [optional json-post-value]

This script attempts to simplify working directly with the Nova OpenStack
API.  It handles the token request and url prefixing for you.  If you include
a second argument, it posts this as application/json.  Due to perl command
argument weirdness, you must escape the quotes in your JSON and wrap the
entire command in double quotes.  (See example.)

Options:

	-p pretty print JSON output through 'python -mjson.tool'

Examples:

	Get a list of servers:
	nova_query.pl /servers.xml
	nova_query.pl /servers.json
	
	Show a specific server's details:
	nova_query.pl /servers/1234.xml
	
	Show only images named uec-natty pretty-printed:
	nova_query.pl -p /images.json?name=uec-natty

	Create a new server named 'Server 1':
	nova_query.pl /servers.xml /\
"{\"server\": {\"name\": \"Server 1\", \"imageRef\": 1, \"flavorRef\": 1}}"

Note:

	NOVA_API_KEY, NOVA_USERNAME, NOVA_PROJECT_ID and NOVA_URL environment
	variables must be set.
EOT
		exit;
	};
};
