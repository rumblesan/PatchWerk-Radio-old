#!/bin/bash

#meant to be run from a directory containing the
#PatchWerk-Radio and Radio-Patches repositories

usage()
{
cat << EOF
usage: $0 options

This script sets up PatchWerk Radio

MANDATORY:
   -d      The PatchWerk Radio repository
   -p      The Radio Patches repository
   -c      The configfile

OPTIONS:
   -h      Show this message
   -n      The name of the PatchWerk instance (Defaults to TestPatchWerk)
   -b      The git branch to checkout         (Defaults to master)
EOF
}

INSTNAME=TestPatchWerk
BRANCH=master
CONFIG=
APPREPO=
PATCHREPO=

while getopts "n:b:c:d:p:" OPTION
do
    case $OPTION in
        h)
            usage
            exit 1
            ;;
        n)
            INSTNAME=$OPTARG
            ;;
        b)
            BRANCH=$OPTARG
            ;;
        c)
            CONFIG=$OPTARG
            ;;
        d)
            APPREPO=$OPTARG
            ;;
        p)
            PATCHREPO=$OPTARG
            ;;
        ?)
            usage
            exit 1
            ;;
    esac
done

if [ -z $CONFIG ] || [ -z $APPREPO ] || [ -z $PATCHREPO ]
then
    usage
    exit 1
fi

BINDIR=/usr/local/sbin/$INSTNAME
WORKDIR=/var/$INSTNAME
PATCHDIR=$WORKDIR/patches
TMPDIR=$WORKDIR/temp

#checkout the correct branches
cd $APPREPO
sudo -u guy git checkout $BRANCH

cd $PATCHREPO
sudo -u guy git checkout master


cd ..

# Clear out the binary dir and then copy the correct files into it
rm -r $BINDIR
mkdir -p $BINDIR
cp -r $APPREPO/app/*         $BINDIR/

#if the config file exists in the same directory
#copy it to the bindir
if [ -f $CONFIG ]
then
    echo using the config file here
    cp  $CONFIG $BINDIR/
fi

#give files the correct permissions
chmod 754 $BINDIR/PatchWerk.py
chown -R patchwerk:radio $BINDIR


# Clear out the patch directory, then copy the new patches back into it
rm -r $WORKDIR
mkdir -p $PATCHDIR
cp -r $PATCHREPO/* $PATCHDIR/
rm -r $PATCHDIR/README

mkdir -p $TMPDIR

#fix permissions
chown -R patchwerk:radio $WORKDIR
chmod -R 755 $WORKDIR



