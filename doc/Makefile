all: rubber.info

rubber.info: rubber.texi
	makeinfo rubber.texi

rubber.dvi: rubber.texi
	texi2dvi rubber.texi

html:
	makeinfo --html --css-include=style-import.css --no-split -o rh rubber.texi

rubber.html: rubber.texi html-patch.ed
	makeinfo --html --css-include=style-import.css --no-split --no-headers -o rubber.html rubber.texi
	ed -s rubber.html < html-patch.ed

distclean clean:
	rm -f rubber.aux rubber.cp rubber.dvi rubber.fn rubber.fns \
		rubber.info rubber.ky rubber.log rubber.pg \
		rubber.toc rubber.tp rubber.vr rubber.vrs
