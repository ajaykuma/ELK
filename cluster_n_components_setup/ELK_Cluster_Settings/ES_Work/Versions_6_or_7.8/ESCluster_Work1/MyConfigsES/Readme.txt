#These are my cluster configs where in I have 3 nodes: c1, c2, c3
--only c1 is master eligible & is for bootstrapping
--ideally we should have 3 master eligible nodes and they should be used for bootstrapping to provide fault tolerance--c2,c3 are data eligible
--data1 (c2) and data2(c3) will be connecting to c1 to get cluster state info

If you setup 3 nodes with hostnames as c1,c2,c3 and enable password less ssh, then you can just download the
'MyConfigES' folder and copy the 'elasticsearch.yml' file from nodex folders to your nodes respectively

For example:
If git folder was downloaded on c1

#my path of elasticsearch is /usr/local/elasticsearch, user is 'elk'
#for more details on setting up nodes and elasticsearch refer 'Cluster_SetupES.txt'

On c1
$cp <pathoffolder>/Node1/elasticsearch.yml /usr/local/elasticsearch/config/

from c1 to c2
$scp <pathoffolder>/Node2/elasticsearch.yml elk@c2:/usr/local/elasticsearch/config/

from c1 to c3
$scp <pathoffolder>/Node3/elasticsearch.yml elk@c3:/usr/local/elasticsearch/config/
