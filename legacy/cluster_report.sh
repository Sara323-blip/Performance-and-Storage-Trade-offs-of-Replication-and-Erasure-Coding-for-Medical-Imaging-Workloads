#!/bin/bash

echo "=========================================="
echo "MINIO CLUSTER HEALTH REPORT"
echo "=========================================="

echo -e "\n📊 Cluster Status:"
mc admin info myminio

echo -e "\n💾 Storage Usage Per Node:"
for node in minio1 minio2 minio3 minio4 minio5; do
    echo -e "\n$node:"
    docker exec $node df -h /data1 | tail -1
done

echo -e "\n📁 Object Count:"
mc ls myminio/dicom-images --recursive | wc -l

echo -e "\n🔧 Erasure Coding Info:"
mc admin info myminio --json | python3 -c "
import sys, json
data = json.load(sys.stdin)
if 'info' in data:
    print(f\"  Drives: {data['info'].get('drives', 'N/A')}\")
    print(f\"  Erasure sets: {data['info'].get('erasure_sets', 'N/A')}\")
"

echo -e "\n✅ Report complete"
