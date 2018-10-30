# include root makefile
ifndef ROOT_MAKEFILE_MK
include ../Makefile
endif

# prevent rules from being evaluated/included multiple times
ifndef $(abspath $(lastword $(MAKEFILE_LIST)))_MK
$(abspath $(lastword $(MAKEFILE_LIST)))_MK := 1


# The following are control variables that determine what logic from `rules.mk` is enabled

# `true`/`false` to enable/disable the actual unit test command so it can be overridden (the targets are still created)
# applies to both the pony and elixir test targets
$(abspath $(lastword $(MAKEFILE_LIST)))_UNIT_TEST_COMMAND := false

# `true`/`false` to enable/disable generate pony related targets (build/test/clean) for pony sources in this directory
# otherwise targets only get created if there are pony sources (*.pony) in this directory.
$(abspath $(lastword $(MAKEFILE_LIST)))_PONY_TARGET := false

# `true`/`false` to enable/disable generate final file build target using ponyc command for the pony build target so
# it can be overridden manually
$(abspath $(lastword $(MAKEFILE_LIST)))_PONYC_TARGET := false

# `true`/`false` to enable/disable generate exs related targets (build/test/clean) for elixir sources in this directory
# otherwise targets only get created if there are elixir sources (*.exs) in this directory.
$(abspath $(lastword $(MAKEFILE_LIST)))_EXS_TARGET := false

# `true`/`false` to enable/disable generate docker related targets (build/push) for a Dockerfile in this directory
# otherwise targets only get created if there is a Dockerfile in this directory
$(abspath $(lastword $(MAKEFILE_LIST)))_DOCKER_TARGET := false

# `true`/`false` to enable/disable recursing into Makefiles of subdirectories if they exist
# (and by recursion every makefile in the tree that is referenced)
$(abspath $(lastword $(MAKEFILE_LIST)))_RECURSE_SUBMAKEFILES := false


# standard rules generation makefile
include $(rules_mk_path)


# PYTHON_FLAGS = off
# ifeq ($(python2),on)
# PYTHON_FLAGS = on
# endif
# ifeq ($(python3),on)
# PYTHON_FLAGS = on
# endif
# ifeq ($(PYTHON_FLAGS),off)
# $(error pywallaroo requires either python3 or python2 to be turned on.)
# endif


# Set up our pywallaroo specific paths. We don't know what directory make was
# run from, so we get an absolute path based on $(wallaroo_path). This will work
# whether make was run from the top level of Wallaroo or from within the
# pywallaroo directory.
PYWALLAROO_PATH = $(wallaroo_path)/pywallaroo
PYWALLAROO_BUILD = $(PYWALLAROO_PATH)/build
PYWALLAROO_CPP = $(PYWALLAROO_PATH)/cpp
ifeq ($(python2),on)
PYWALLAROO_CPP_EXTRA = $(PYWALLAROO_PATH)/cpp/python2/python2-wallaroo
else
PYWALLAROO_CPP_EXTRA = $(PYWALLAROO_PATH)/cpp/python3/python3-wallaroo
endif
WALLAROO_LIB =  $(wallaroo_path)/lib

UNAME_S = $(shell uname -s)

ifeq ($(python3),on)
PYTHON3 = python3
#PYTHON3 = python3-dbg
PYTHON3_INCLUDES = $(shell $(PYTHON3)-config --includes)
PYTHON3_LIBS = $(shell $(PYTHON3)-config --libs)
ifeq ($(UNAME_S),Darwin)
PYTHON3_LIBS += $(shell $(PYTHON3)-config --ldflags)
PYTHON3_EXTRAS = --linker '$(LD) $(PYTHON3_LIBS)'
else
PYTHON3_EXTRAS = --linker '$(CC) $(PYTHON3_LIBS)'
endif
else
PYTHON3_INCLUDES =
PYTHON3_LIBS =
PYTHON3_EXTRAS =
endif


# Our top level Makefile has 3 rules that would have been generated for us if
# we hadn't turned them off at the top of the Makefile. Here we recreate them
# with our own custom rules. This allows the top level commands like
# "make test" to work.
build-pywallaroo: pywallaroo_build
build-pywallaroo2: pywallaroo_build2
unit-tests-pywallaroo: build-pywallaroo
unit-tests-pywallaroo: wallaroo_unit_tests
unit-tests-pywallaroo2: build-pywallaroo2
unit-tests-pywallaroo2: wallaroo_unit_tests
clean-pywallaroo: pywallaroo_clean

pywallaroo_clean:
	$(QUIET)rm -rf $(PYWALLAROO_BUILD)
	$(QUIET)rm -f $(PYWALLAROO_PATH)/pywallaroo.d
	$(QUIET)rm -rf $(PYWALLAROO_PATH)/.deps


wallaroo_unit_tests:
	cd $(PYWALLAROO_PATH) && \
		python2 -m pytest --color=yes --tb=native --verbose test/wallaroo_test.py && \
		python3 -m pytest --color=yes --tb=native --verbose --exitfirst test/wallaroo_test.py

pywallaroo_build: $(PYWALLAROO_BUILD)/pywallaroo

-include $(PYWALLAROO_PATH)/pywallaroo.d
$(PYWALLAROO_BUILD)/pywallaroo: EXTRA_PONYCFLAGS= --output=$(PYWALLAROO_BUILD) --path=$(PYWALLAROO_BUILD) $(PYTHON3_EXTRAS)
$(PYWALLAROO_BUILD)/pywallaroo: $(PYWALLAROO_BUILD)/libpython-wallaroo.a
	$(call PONYC,$(abspath $(PYWALLAROO_PATH:%/=%)))

$(PYWALLAROO_BUILD)/libpython-wallaroo.a: $(PYWALLAROO_BUILD)/python-wallaroo.o
	$(QUIET)ar rvs $(PYWALLAROO_BUILD)/libpython-wallaroo.a $(PYWALLAROO_BUILD)/python-wallaroo.o

$(PYWALLAROO_BUILD)/python-wallaroo.o: $(PYWALLAROO_CPP_EXTRA).c $(PYWALLAROO_CPP)/python-wallaroo.h
	$(QUIET)mkdir -p $(PYWALLAROO_BUILD)
	$(QUIET)cc -g -o $(PYWALLAROO_BUILD)/python-wallaroo.o $(PYTHON3_INCLUDES) -c $(PYWALLAROO_CPP_EXTRA).c

# end of prevent rules from being evaluated/included multiple times
endif
