echo '{"array": ["dummy"], "variable": "dummy"}' > .mustache_config.json
for yamlfile in $(find . -name "*.yml" -o -name "*.yaml"); do

    filename=$(basename -- "$yamlfile")
    extension="${filename##*.}"
    filename="${filename%.*}"
    test_config=".github/resources/$filename.config.json"

    if [ -e "$test_config" ]; then
        mustache $test_config $yamlfile > $yamlfile
    else
        sed "s|{{\([/#]\)[^}]*}}|{{\1array}}|g" $yamlfile > expanded.tmp  # replace mustache arrays
        sed -i "s|{{[^#/].\{1,\}}}|{{variable}}|g" expanded.tmp           # replace mustache variables
        mustache .mustache_config.json expanded.tmp > $yamlfile           # perform mustache expansion overwriting original file
    fi

done
rm expanded.tmp
