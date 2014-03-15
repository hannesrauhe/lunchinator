REPO_DIR=/var/www/hana-students/
MAJOR_VERSION=2

all: linux/lunchinator.deb linux/lunchinator-nodep.deb linux/lunchinator.rpm

linux:
	mkdir linux

clean:
	rm -r linux

linux/lunchinator.deb: linux
	grep -v "Version:" deb_build/DEBIAN/control > deb_build/DEBIAN/control.noversion
	echo Version: $(MAJOR_VERSION).`git rev-list HEAD --count` >> deb_build/DEBIAN/control.noversion 
	mv deb_build/DEBIAN/control.noversion deb_build/DEBIAN/control
	sudo chown -R root:root deb_build
	dpkg --build deb_build linux/lunchinator.deb
	lintian linux/lunchinator.deb
	dpkg-sig -k 17F57DC2 --sign builder linux/lunchinator.deb
	sudo chown -R ${USER}:${USER} deb_build

linux/lunchinator-nodep.deb:
	sed -e 's/lunchinator/lunchinator-nodep/g' deb_build/DEBIAN/control > deb_build/DEBIAN/control.nodep
	mv deb_build/DEBIAN/control deb_build/DEBIAN/control.bak
	grep -v "Depends:" deb_build/DEBIAN/control.nodep > deb_build/DEBIAN/control
	sudo chown -R root:root deb_build
	dpkg --build deb_build linux/lunchinator-nodep.deb
	dpkg-sig -k 17F57DC2 --sign builder linux/lunchinator-nodep.deb
	sudo chown -R ${USER}:${USER} deb_build
	mv deb_build/DEBIAN/control.bak deb_build/DEBIAN/control	
	rm deb_build/DEBIAN/control.nodep

linux/lunchinator.rpm: linux/lunchinator.deb
	cd linux && sudo alien -r -k lunchinator.deb
	sudo chown ${USER}:${USER} linux/*.rpm

#in case we want to set up reprepro again:
#install: lunchinator.deb lunchinator-nodep.deb
#	echo "          IF THIS FAILS, INCREMENT THE VERSION IN THE CONTROL FILE"
#	reprepro -Vb $(REPO_DIR) remove hana-students lunchinator.deb
#	reprepro -Vb $(REPO_DIR) includedeb hana-students lunchinator.deb
#	reprepro -Vb $(REPO_DIR) includedeb hana-students lunchinator-nodep.deb

.PHONY: installer/lunchinator.deb installer/lunchinator-nodep.deb

owner:
	sudo chown -R ${USER}:${USER} deb_build
	find deb_build -type d -exec chmod 755 {} \;
	find deb_build -type f -exec chmod 644 {} \;
	chmod +x deb_build/usr/bin/lunchinator
