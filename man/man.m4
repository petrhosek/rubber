divert(-1)
changesyntax(`@\')
\changequote([, ])

This file contains m4 macros used to make man pages. These macros are meant to
be compatible with my set of macros for producing HTML and with the associated
TeX format.

I put these macros under the GPL license, if anyone cares.

** Sectioning

\define(init, [])

\define(title, [\define(the_title, [$1])])
\define(man_descr, [\define(the_descr, [$1])])
\define(man_section, [\define(the_section, [$1])])

\define(part,
[\ifelse([$1], [main], [\divert(0)\dnl
.\" This file was automatically generated (by my m4 macros).
.TH \the_title \the_section
.IX \the_title
.SH NAME
\the_title \- \the_descr],
[\ifelse([$1], [man], [\divert(0)],
[\divert(-1)])])])

\define(uppercase, [\translit([[$1]], [a-z], [A-Z])])
\define(section, [\ifelse([$1], 2, [.SH \uppercase([$2])], [.SS [$2]])])

\define(bye, [])


** Environments

\define([define_env], [\define([begin:$1], [$2])\define([end:$1], [$3])])
\define(begin, [\indir([begin:$1], \shift($@))[]])
\define(end, [\indir([end:$1])])

\define_env(subtitle)
\define_env(intro)

\define_env(description,
[\descr_begin\pushdef(descr_begin, [.RS])\pushdef(descr_end, [.RE])\dnl
\pushdef(item, \defn(descr_item))],
[\popdef(item)\popdef(descr_begin)\popdef(descr_end)\descr_end])
\define(descr_begin, [])
\define(descr_end, [])
\define(descr_item, [.TP
.B $1
$2])

\define_env(example, [.nf
], [
.fi])

** Formatting

\define(bf, [\fB$1\fR])
\define(em, [\fI$1\fR])
\define(tt, [$1])

\define(dash, [\-])
\define(ddash, [\-\-])

\define(br, [])

\define(lbrack, [\changequote({,}){[}\dnl]
\changequote([,])])
\define(rbrack, [\changequote({,})\dnl[
{]}\changequote([,])])

\define(arg, [\em([$1])])
\define(narg, [\em([<$1>])])
\define(optarg, [\lbrack\em([$1])\rbrack])
\define(dopt, [\arg([\dash[]$1])])
\define(ddopt, [\arg([\ddash[]$1])])
\define(cmd, [\bf([$1])])

\define(syntax, [.B [$1]
$2])

\define(manref, [.BR $1 ($2)])
\define(link, [$1 <$2>])
