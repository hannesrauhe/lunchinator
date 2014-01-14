REPO_DIR=/var/www/hana-students/

all: lunchinator.deb lunchinator-nodep.deb lunchinator.rpm

lunchinator.deb:
	sudo chown -R root:root deb_build
	dpkg --build deb_build lunchinator.deb
	lintian lunchinator.deb
	dpkg-sig -k AF32F68C --sign builder lunchinator.deb
	sudo chown -R ${USER}:${USER} deb_build

lunchinator-nodep.deb:
	sed -e 's/lunchinator/lunchinator-nodep/g' deb_build/DEBIAN/control > deb_build/DEBIAN/control.nodep
	mv deb_build/DEBIAN/control deb_build/DEBIAN/control.bak
	grep -v "Depends:" deb_build/DEBIAN/control.nodep > deb_build/DEBIAN/control
	sudo chown -R root:root deb_build
	dpkg --build deb_build lunchinator-nodep.deb
	dpkg-sig -k AF32F68C --sign builder lunchinator-nodep.deb
	sudo chown -R ${USER}:${USER} deb_build
	mv deb_build/DEBIAN/control.bak deb_build/DEBIAN/control	
	rm deb_build/DEBIAN/control.nodep

lunchinator.rpm:
	sudo alien -r lunchinator.deb
	sudo chown ${USER}:${USER} *.rpm

install: lunchinator.deb lunchinator-nodep.deb
	echo "          IF THIS FAILS, INCREMENT THE VERSION IN THE CONTROL FILE"
#	reprepro -Vb $(REPO_DIR) remove hana-students lunchinator.deb
	reprepro -Vb $(REPO_DIR) includedeb hana-students lunchinator.deb
	reprepro -Vb $(REPO_DIR) includedeb hana-students lunchinator-nodep.deb

.PHONY: lunchinator.deb lunchinator-nodep.deb

owner:
	sudo chown -R ${USER}:${USER} deb_build
	find deb_build -type d -exec chmod 755 {} \;
	find deb_build -type f -exec chmod 644 {} \;
	chmod +x deb_build/usr/bin/lunchinator
