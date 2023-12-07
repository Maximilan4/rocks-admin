# [POC] Rocks admin
Just proof of concept for an alternative version of luarocks-admin with a next targets:
- upload file/files with patching current server manifest [x]
- remove file/files with patching current server manifest [x]
- show rockspec of specific package on server [v]
- show dependencies of specific package [v]
- show current manifest [v]

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

## usage
```bash
# show current manifest packages with versions
python rocks-admin.py --server=http://moonlibs.github.io/rocks manifest
1. background:
        - scm-1 [rockspec]
2. base58:
        - scm-1 [rockspec]
...
# can search specific package name
python rocks-admin.py --server=http://moonlibs.github.io/rocks manifest http
1. http:
        - scm-1 [rockspec]
        - 1.0.1 [rockspec]
        - 1.0.2 [rockspec]

# shows content of specific rockspec
python rocks-admin.py --server=http://moonlibs.github.io/rocks rockspec http@1.0.2 show

# shows dependencies with src.rock existance check on a server
python rocks-admin.py --server=http://moonlibs.github.io/rocks rockspec spacer deptree --check-arch=src
         lua >= 5.1, [✓, excluded]
         inspect >= 3.1.0-1, [x, not found in manifest]
         moonwalker >= 0.1.0, [scm-1 src: manifest(x)/file(x) ]
                 lua >= 5.1, [✓, excluded]
   
```