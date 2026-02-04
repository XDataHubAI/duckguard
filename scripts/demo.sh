#!/bin/bash
# DuckGuard v3.2 Demo Script
# Run this to generate a terminal demo

cd /home/oc01/.openclaw/workspace/duckguard
source .venv/bin/activate

clear
echo "$ pip install duckguard"
sleep 1
echo "Successfully installed duckguard-3.2.0"
sleep 1.5

echo ""
echo "$ python"
sleep 0.5
echo ">>> from duckguard import connect"
sleep 0.8
echo ">>> orders = connect('examples/sample_data/orders.csv')"
sleep 0.8
echo ">>> orders.customer_id.is_not_null()"
sleep 0.5

python -c "
from duckguard import connect
ds = connect('examples/sample_data/orders.csv')
print(repr(ds.customer_id.is_not_null()))
"
sleep 1.5

echo ">>> orders.amount.between(0, 10000)"
sleep 0.5
python -c "
from duckguard import connect
ds = connect('examples/sample_data/orders.csv')
print(repr(ds.amount.between(0, 10000)))
"
sleep 1.5

echo ">>> orders.score()"
sleep 0.5
python -c "
from duckguard import connect
ds = connect('examples/sample_data/orders.csv')
print(repr(ds.score()))
"
sleep 2

echo ">>> exit()"
sleep 0.5
echo ""
echo "$ duckguard profile examples/sample_data/orders.csv"
sleep 1

duckguard profile examples/sample_data/orders.csv
sleep 3

echo ""
echo "$ duckguard anomaly examples/sample_data/orders.csv"
sleep 1

duckguard anomaly examples/sample_data/orders.csv
sleep 3

echo ""
echo "# AI-powered features (v3.2)"
echo "$ duckguard explain examples/sample_data/orders.csv"
echo "$ duckguard suggest examples/sample_data/orders.csv"
echo "$ duckguard fix examples/sample_data/orders.csv"
sleep 2
