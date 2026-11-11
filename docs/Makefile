SPHINXBUILD ?= sphinx-build
SOURCEDIR = .
BUILDDIR = _build
SPHINXOPTS ?=

.PHONY: html clean linkcheck

html:
	$(SPHINXBUILD) -b html $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/html"

clean:
	rm -rf "$(BUILDDIR)"

linkcheck:
	$(SPHINXBUILD) -b linkcheck $(SPHINXOPTS) "$(SOURCEDIR)" "$(BUILDDIR)/linkcheck"
