for i in {1..10}
do
    for folder_name in $(ls -d ./valid_folders_archive/*/)
    do
        one=${folder_name#*archive/}
        two=${one%/*}
        echo $two
        python mcts_expansion.py $two
        wait 1
    done
done
