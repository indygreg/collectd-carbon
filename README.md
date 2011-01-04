collectd-carbon - Write Collectd to Carbon

Collectd is a metrics collection daemon. Carbon is a frontend to Whisper, which is a storage engine (similar to RRD). At this time, Carbon and Whisper are likely encountered alongside [Graphite](http://graphite.wikidot.com/start), a nifty real-time graphing application.

This Collectd plugin is implemented in Python, which means it will require the Python plugin to Collect, which itself requires Collectd 4.9.

The plugin requires some configuration. This is done by passing parameters via the <Module> config section in your Collectd config. The following parameters are recognized:

* LineReceiverHost - hostname or IP address where a Carbon line receiver is listening
* LineReceiverPort - port on which line receiver is listening
* TypesDB - file defining your Collectd types. This should be the sames as your TypesDB global config parameters. This is needed so the plugin can associate proper names for each data field within complex types. The plugin has to reparse the types files for the names because the Collectd Python API does not provide the means to extract them (the Perl and Java APIs do, however). If you do not define this parameter or do not have complete parameter definition, the plugin will spew errors for unknown data types.
* DeriveCounters - If present, the plugin will normalize COUNTER and DERIVE types by recording the difference between two subsequent values. See the section below.

#Data Mangling

Collectd data is collected/written in discrete tuples having the following:

    (host, plugin, plugin_instance, type, type_instance, time, interval, metadata, values)

_values_ is itself a list of { counter, gauge, derive, absolute } (numeric) values. To further complicate things, each distinct _type_ has its own definition corresponding to what's in the _values_ field.

Graphite, by contrast, deals with tuples of ( metric, value, time ). So, we effectively need to mangle all those extra fields down into the _metric_ value.

This plugin mangles the fields to the metric name:

    host.plugin[.plugin_instance].type[.type_instance].data_source

Where *data_source* is the name of the data source (i.e. ds_name) in the type being written.

For example, the Collectd distribution has a built-in _df_ type:

    df used:GAUGE:0:1125899906842623, free:GAUGE:0:1125899906842623

The *data_source* values for this type would be *used* and *free* yielding the metrics (along the lines of) *hostname_domain.plugin.df.used* and *hostname_domain.plugin.df.free*.

## COUNTER and DERIVE Types

Collectd data types, like RRDTool, differentiate between ABSOLUTE, COUNTER, DERIVE, and GAUGE types. When values are stored in RRDTool, these types invoke special functionality. However, they do nothing special in Carbon. And, if you are using Graphite, they complicate matters because you'll want to apply a derivative function to COUNTER and DERIVE types to obtain any useful values.

When the plugin is configured with the *DeriveCounters* flag, the plugin will send the difference between two data points to Carbon. Please note the following regarding behavior:

* Data is sent to Carbon after receiving the 2nd data point. This is because the plugin must establish an initial value to calculate the difference from said value.
* The plugin is aware of the minimum and maximum values and will handle overflows and wrap-arounds properly.
* An overflow for a type with max value *U* is treated as an initial value. i.e. you will lose one data point.
* A minimum value of *U* is treated as *0*.
