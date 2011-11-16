# Introduction

collectd-carbon is a [collectd](http://www.collectd.org/) plugin that
writes obtained values to Carbon.

Carbon is a frontend to Whisper, which is a storage engine (similar to
RRD). At this time, Carbon and Whisper are likely encountered alongside
[Graphite](http://graphite.wikidot.com/start), a nifty real-time
graphing application.

Short version: collectd-carbon is an alternative data writer to RRD.

# Requirements

* Collectd 4.9 or later (for the Python plugin) (A patch may be required
  to fix the Python plugin - see below)
* Python 2.4 or later
* A running Carbon LineReceiver server (such as *carbon-cache.py*)

If you don't have Python configured and still wish to write Collectd
information to Graphite/Carbon, see
https://github.com/jssjr/collectd-write_graphite for a similar plugin
written in C.

# Version Information

collectd-carbon does not currently maintain release versions. The policy
(at least on indygreg's original Github repository) is that the *master*
branch should always be stable and production ready.

As always, it is probably best to exercise discretion. If a commit has
landed recently, you may want to consider looking it over and/or waiting
a little while for others to test it for you.

# Configuration

The plugin requires some configuration. This is done by passing
parameters via the <Module> config section in your Collectd config. The
following parameters are recognized:

* LineReceiverHost - hostname or IP address where a Carbon line receiver
  is listening
* LineReceiverPort - port on which line receiver is listening
* TypesDB - file(s) defining your Collectd types. This should be the
  sames as your TypesDB global config parameters. If not specified, the
  plugin will not work.
* DifferentiateCounters - If present, the plugin will normalize COUNTER
  and DERIVE types by recording the difference between two subsequent
  values. See the section below.
* DifferentiateCountersOverTime - If present, the plugin will divide
  the values of COUNTER and DERIVE types by the interval between the
  two subsequent values. Implies DifferentiateCounters. See the section
  below.
* LowercaseMetricNames - If present, all metric names will be converted
  to lower-case.
* MetricPrefix - If present, all metric names will contain this string
  prefix. Do not include a trailing period.
* HostPostfix - If present, all hostnames will contain this string
  postfix (my_host_name.HostPostfix). Do not include a trailing period.
* HostSeparator - If present, will change the default behavior of
  inserting a "_" between the hostname (my_host_name) to this value.
* MetricSeparator - If present, will change the default behavior of inserting
  a "." within type and type_instances. This can be used to prevent deep
  paths in Graphite/carbon for IPs and hostnames.

## Example

The following is an example Collectd configuration for this plugin:

    <LoadPlugin "python">
        Globals true
    </LoadPlugin>

    <Plugin "python">
        # carbon_writer.py is at path /opt/collectd-plugins/carbon_writer.py
        ModulePath "/opt/collectd-plugins/"

        Import "carbon_writer"

        <Module "carbon_writer">
            LineReceiverHost "myhost.mydomain"
            LineReceiverPort 2003
            DifferentiateCountersOverTime true
            LowercaseMetricNames true
            TypesDB "/usr/share/collectd/types.db"
        </Module>
    </Plugin>

# Operational Notes

If the connection to the line receiver cannot be established or goes
bad, the plugin will automatically attempt to reconnect. If connections
fail, the plugin will reconnect at most once every 10 seconds. This
prevents many likely failures from occurring when the server is down.

The plugin needs to parse Collectd type files. If there was an error
parsing a specific type (look for log messages at Collectd startup
time), the plugin will fail to write values for this type. It will
simply skip over them and move on to the next value. It will write a log
message every time this happens so you can correct the problem.

The plugin needs to perform redundant parsing of the type files because
the Collectd Python API does not provide an interface to the types
information (unlike the Perl and Java plugin APIs). Hopefully this will
be addressed in a future version of Collectd.

# Data Mangling

Collectd data is collected/written in discrete tuples having the
following:

    (host, plugin, plugin_instance, type, type_instance, time, interval, metadata, values)

_values_ is itself a list of { counter, gauge, derive, absolute }
(numeric) values. To further complicate things, each distinct _type_ has
its own definition corresponding to what's in the _values_ field.

Graphite, by contrast, deals with tuples of ( metric, value, time ). So,
we effectively need to mangle all those extra fields down into the
_metric_ value.

This plugin mangles the fields to the metric name:

    host.plugin[.plugin_instance].type[.type_instance].data_source

Where *data_source* is the name of the data source (i.e. ds_name) in the
type being written.

For example, the Collectd distribution has a built-in _df_ type:

    df used:GAUGE:0:1125899906842623, free:GAUGE:0:1125899906842623

The *data_source* values for this type would be *used* and *free*
yielding the metrics (along the lines of)
*hostname_domain.plugin.df.used* and *hostname_domain.plugin.df.free*.

## COUNTER and DERIVE Types

Collectd data types, like RRDTool, differentiate between ABSOLUTE,
COUNTER, DERIVE, and GAUGE types. When values are stored in RRDTool,
these types invoke special functionality. However, they do nothing
special in Carbon. And, if you are using Graphite, they complicate
matters because you'll want to apply a derivative function to COUNTER
and DERIVE types to obtain any useful values.

When the plugin is configured with the *DifferentiateCounters* flag,
the plugin will send the difference between two data points to Carbon.
Please note the following regarding behavior:

* Data is sent to Carbon after receiving the 2nd data point. This is
  because the plugin must establish an initial value from which to
  calculate the difference.
* The plugin is aware of the minimum and maximum values and will handle
  overflows and wrap-arounds properly.
* An overflow for a type with max value *U* is treated as an initial
  value. i.e. you will lose one data point.
* A minimum value of *U* is treated as *0*.

Please note that *DifferentiateCounters* stores the difference, not the
actually time-derivative, between 2 values. This can lead to some
unexpected, but still valid, behavior. For example, with a Collectd
polling interval of 10s, values dispatches from the CPU plugin will be
normalized to around 1000 (100 per each second). RRD, by contrast, would
normalize values to around 100. If graphed, the values should form the
same shapes, but off by a scale of 10:1.

If *DifferentiateCountersOverTime* is configured, the actual
time-derivative betwen the values is stored. This results in CPU plugin
results that are normalized to around 100 (like RRD).

*DifferentiateCountersOverTime* implies *DifferentiateCounters*.

# Troubleshooting

You can see the raw values dispatched to carbon by packet sniffing:

    $ sudo ngrep -qd any . tcp dst port 2003

## Collectd Python Write Callback Bug

Collectd versions through 4.10.2 and 4.9.4 have a bug in the Python
plugin where Python would receive bad values for certain data sets. The
bug would typically manifest as data values appearing to be 0. The
original author of this plugin identified the bug and sent a fix to the
Collectd development team.

Collectd versions 4.9.5, 4.10.3, and 5.0.0 are the first official
versions with a fix for this bug. If you are not running one of these
versions or have not applied the fix (which can be seen at
<https://github.com/indygreg/collectd/commit/31bc4bc67f9ae12fb593e18e0d3649e5d4fa13f2>),
you will likely dispatch wrong values to Carbon.

## Collectd 4.10.3 on EL5 ImportError

Using the plugin with collectd-4.10.3 from EPEL5 on RHEL or CentOS 5.x
may produce the following error:

    Jul 20 14:54:38 mon0 collectd[2487]: plugin_load_file: The global flag is not supported, libtool 2 is required for this.
    Jul 20 14:54:38 mon0 collectd[2487]: python plugin: Error importing module "carbon_writer".
    Jul 20 14:54:38 mon0 collectd[2487]: Unhandled python exception in importing module: ImportError: /usr/lib64/python2.4/lib-dynload/_socketmodule.so: undefined symbol: PyExc_ValueError
    Jul 20 14:54:38 mon0 collectd[2487]: python plugin: Found a configuration for the "carbon_writer" plugin, but the plugin isn't loaded or didn't register a configuration callback.
    Jul 20 14:54:38 mon0 collectd[2488]: plugin_dispatch_values: No write callback has been registered. Please load at least one output plugin, if you want the collected data to be stored.
    Jul 20 14:54:38 mon0 collectd[2488]: Filter subsystem: Built-in target `write': Dispatching value to all write plugins failed with status 2 (ENOENT). Most likely this means you didn't load any write plugins.

This may also occur on other operating systems. It is caused by a
libtool/libltdl quirk described in [this mailing list thread](http://mailman.verplant.org/pipermail/collectd/2008-March/001616.html).
As per the workarounds detailed there, you may either:

 1. Modify the init script.

        @@ -25,7 +25,7 @@
                echo -n $"Starting $prog: "
                if [ -r "$CONFIG" ]
                then
        -               daemon /usr/sbin/collectd -C "$CONFIG"
        +               LD_PRELOAD=/usr/lib64/libpython2.4.so daemon /usr/sbin/collectd -C "$CONFIG"
                        RETVAL=$?
                        echo
                        [ $RETVAL -eq 0 ] && touch /var/lock/subsys/$prog

 1. Modify the RPM and rebuild.

        @@ -182,7 +182,7 @@


         %build
        -%configure \
        +%configure CFLAGS=-"DLT_LAZY_OR_NOW='RTLD_LAZY|RTLD_GLOBAL'" \
             --disable-static \
             --disable-ascent \
             --disable-apple_sensors \
