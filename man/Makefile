# This is the makefile for Rubber's man pages.
#
# It is only included in the CVS version, to generate the pages from their
# templates using my M4 macros. The templates and the macros are not
# included in the packages.
#
# This file is covered by the GPL, as part of Rubber.
# (c) Emmanuel Beffara, 2002

PG = $(wildcard */*.pg)
MAN = $(subst .pg,,$(PG))

all: $(MAN)

%: %.pg man.m4
	m4 man.m4 $< > $@

clean:
	rm -f $(MAN)
