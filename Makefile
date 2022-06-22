# --- Detecting OS
ifeq '$(findstring ;,$(PATH))' ';'
    detected_OS := Windows
else
    detected_OS := $(shell uname 2>/dev/null || echo Unknown)
    detected_OS := $(patsubst CYGWIN%,Cygwin,$(detected_OS))
    detected_OS := $(patsubst MSYS%,MSYS,$(detected_OS))
    detected_OS := $(patsubst MINGW%,MSYS,$(detected_OS))
endif

testfile= weio/weio/tests/example_files/FASTIn_arf_coords.txt
all:
ifeq ($(detected_OS),Darwin)        # Mac OS X
	./pythonmac pyDatView.py $(testfile)
else
	python pyDatView.py $(testfile)
endif




deb:
	python DEBUG.py

install:
	python setup.py install

dep:
	python -m pip install -r requirements.txt

pull:
	git pull --recurse-submodules
update:pull


help:
	@echo "Available rules:"
	@echo "   all        run the standalone program"
	@echo "   install    install the python package in the system" 
	@echo "   dep        download the dependencies " 
	@echo "   pull       download the latest version " 
	@echo "   test       run the unit tests " 

test:
ifeq ($(detected_OS),Darwin)        # Mac OS X
	./pythonmac -m unittest discover -v tests
	./pythonmac -m unittest discover -v pydatview/plugins/tests
else
	python -m unittest discover -v tests
	python -m unittest discover -v pydatview/plugins/tests
endif

prof:
	python -m cProfile -o tests/prof_all.prof  tests/prof_all.py
	python -m pyprof2calltree -i tests/prof_all.prof -o tests/callgrind.prof_all.prof
	snakeviz tests/prof_all.prof


exe:
	python -m nuitka --follow-imports --include-plugin-directory --include-plugin-files --show-progress --show-modules --output-dir=build-nuitka pyDatView.py

exestd:
	python -m nuitka --python-flag=no_site --assume-yes-for-downloads --standalone --follow-imports --include-plugin-directory --include-plugin-files --show-progress --show-modules --output-dir=build-nuitka-std pyDatView.py

clean:
	rm -rf __pycache__
	rm -rf *.egg-info
	rm -rf *.spec
	rm -rf build*
	rm -rf dist
	

pyexe:
	pyinstaller --onedir pyDatView.py

version:
ifeq ($(OS),Windows_NT)
	@echo "Doing nothing"
else
	@sh _tools/setVersion.sh
endif

installer: 
	python -m nsist installer.cfg



