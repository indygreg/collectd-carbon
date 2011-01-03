collectd-carbon - Write Collectd to Carbon

Collectd is a metrics collection daemon. Carbon is a frontend to Whisper, which is a storage engine (similar to RRD). At this time, Carbon and Whisper are likely encountered alongside [Graphite](http://graphite.wikidot.com/start), a nifty real-time graphing application.

This Collectd plugin is implemented in Python, which means it will require the Python plugin to Collect, which itself requires Collectd 4.9.

The plugin requires some configuration. This is done by passing parameters via the <Module> config section in your Collectd config. The following parameters are recognized:

* LineReceiverHost - hostname or IP address where a Carbon line receiver is listening
* LineReceiverPort - port on which line receiver is listening
* TypesDB - file defining your Collectd types. This should be the sames as your TypesDB global config parameters. This is needed so the plugin can associate proper names for each data field within complex types. The plugin has to reparse the types files for the names because the Collectd Python API does not provide the means to extract them (the Perl and Java APIs do, however). If you do not define this parameter or do not have complete parameter definition, the plugin will spew errors for unknown data types.

#Data Mangling

Collectd data is collected/written in discrete tuples having the following:

  (host, plugin, plugin_instance, type, type_instance, time, interval, metadata, values)

_values_ is itself a list of { counter, gauge, derive, absolute } (numeric) values. To further complicate things, each distinct _type_ has its own definition corresponding to what's in the _values_ field.

Graphite, by contrast, deals with tuples of ( metric, value, time ). So, we effectively need to mangle all those extra fields down into the _metric_ value.

This plugin mangles the fields to the metric name:

  host.plugin[.plugin_instance].type[.type_instance].data_source

Where *data_source* is the name of the data source (i.e. ds_name) in the type being written.

For example, the Collectd distribution has a built-in type:

  df used:GAUGE:0:1125899906842623, free:GAUGE:0:1125899906842623

The *data_source* values for this type would be *used* and *free*.
