# Naver Gateway Tool
Tool to help you manage your servers need to be accessed easily.

## Installing
Clone from the github
```
git clone https://github.com/SungJinYoo/naver-gw.git
cd naver-gw
git submodule init
git submodule update
```

## Running
```
python gwkit.py
```

## Migrating existing data
```
python migrate.py LEGACY_GWKIT_DIR/.known_hosts
```
