set -e
export CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7
while true
do
    python -u demo2.py 
done
# GLOG_vmodule=lookup_table_op=4 python -u demo2.py > debug2.log 2>&1

