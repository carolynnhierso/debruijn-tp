#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
import networkx as nx
import matplotlib
from operator import itemgetter
import random
random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt
matplotlib.use("Agg")

__author__ = "Carolynn Hierso"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Carolynn Hierso"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Carolynn Hierso"
__email__ = "carolynn.hierso@etu.u-paris.fr"
__status__ = "Developpement"

def isfile(path):
    """Check if path is an existing file.
      :Parameters:
          path: Path to the file
    """
    if not os.path.isfile(path):
        if os.path.isdir(path):
            msg = "{0} is a directory".format(path)
        else:
            msg = "{0} does not exist.".format(path)
        raise argparse.ArgumentTypeError(msg)
    return path


def get_arguments():
    """Retrieves the arguments of the program.
      Returns: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(description=__doc__, usage=
                                     "{0} -h"
                                     .format(sys.argv[0]))
    parser.add_argument('-i', dest='fastq_file', type=isfile,
                        required=True, help="Fastq file")
    parser.add_argument('-k', dest='kmer_size', type=int,
                        default=22, help="k-mer size (default 22)")
    parser.add_argument('-o', dest='output_file', type=str,
                        default=os.curdir + os.sep + "contigs.fasta",
                        help="Output contigs in fasta file (default contigs.fasta)")
    parser.add_argument('-f', dest='graphimg_file', type=str,
                        help="Save graph as an image (png)")
    return parser.parse_args()


def read_fastq(fastq_file):
    with open(fastq_file) as file: 
        for f in file: 
            yield next(file).strip("\n")
            next(file)
            next(file)

    
def cut_kmer(read, kmer_size):
    for r,_ in enumerate(read[:len(read) - kmer_size + 1]):
        yield read[r:r+kmer_size]
 

def build_kmer_dict(fastq_file, kmer_size):
    dict_kmer={}
    for file in read_fastq(fastq_file):
        for kmer in cut_kmer(file, kmer_size):
            if kmer in dict_kmer.keys(): 
                dict_kmer[kmer]+=1
            else : 
                dict_kmer[kmer]=1
    return  dict_kmer
 


def build_graph(kmer_dict):
    digraph = nx.DiGraph()
    for kmer in kmer_dict: 
        digraph.add_edge(kmer[:-1], kmer[1:], weight=kmer_dict[kmer])
    return digraph

    
def remove_paths(graph, path_list, delete_entry_node, delete_sink_node):
    for path in path_list:
        if delete_entry_node and delete_sink_node:
            graph.remove_nodes_from(path)
        elif delete_entry_node: 
            graph.remove_nodes_from(path[:-1])
        elif delete_sink_node: 
            graph.remove_nodes_from(path[1:])
        else: 
            graph.remove_nodes_from(path[1:-1])
    return graph


def select_best_path(graph, path_list, path_length, weight_avg_list, 
                     delete_entry_node=False, delete_sink_node=False):
    if statistics.stdev(weight_avg_list)>0: 
        del path_list[weight_avg_list.index(max(weight_avg_list))]
        graph = remove_paths(graph, path_list, delete_entry_node, delete_sink_node)
    elif statistics.stdev(path_length)>0:
        del path_list[path_length.index(max(path_length))]
        graph = remove_paths(graph, path_list, delete_entry_node, delete_sink_node)
    else: 
        random.seed(9001)
        del path_list[weight_avg_list.index(random.randint(0,len(path_list)))]
        graph = remove_paths(graph, path_list, delete_entry_node, delete_sink_node)
    return graph        


        

def path_average_weight(graph, path):
    """Compute the weight of a path"""
    return statistics.mean([d["weight"] for (u, v, d) in graph.subgraph(path).edges(data=True)])

def solve_bubble(graph, ancestor_node, descendant_node):
    path_list,path_length,weight_avg_list = [],[],[]
    for path in nx.all_simple_paths(graph,ancestor_node,descendant_node): 
        path_list.append(path)
        path_length.append(len(path))
        weight_avg_list.append(path_average_weight(graph, path))
    graph = select_best_path(graph, path_list, path_length, weight_avg_list, 
                     delete_entry_node=False, delete_sink_node=False)
    return graph
    


def simplify_bubbles(graph):
    bubble = False 
    for n in graph.nodes :
        list_predecessors = list(graph.predecessors(n))
        if len(list_predecessors)>1:
            noeud_n = n
            for c,i in enumerate(list_predecessors):    
                for j in list_predecessors[c+1:]: 
                    ancestor_node = nx.lowest_common_ancestor(graph, i, j)
                    if ancestor_node != None:
                        bubble = True
                        break
        elif bubble : 
            break
    if bubble: 
            graph = simplify_bubbles(solve_bubble(graph,ancestor_node, noeud_n))

    return graph
            
def solve_entry_tips(graph, starting_nodes):
    for node in graph.nodes():
        path_list,path_length,weight_avg_list= [],[],[]        
        tips = False
        list_predecessors = list(graph.predecessors(node))
        if len(list_predecessors) > 1:
            for start in starting_nodes:
                if nx.has_path(graph, start, node):
                    path = list(nx.all_simple_paths(
                        graph, start, node))
                    path_list.append(path[0])
                    path_length.append(len(path[0]))
                    weight_avg_list.append(path_average_weight(graph, path[0]))
                    tips = True
        if tips:
            break
    if tips:
        graph = select_best_path(
            graph, path_list, path_length, weight_avg_list, delete_entry_node=True)
        graph = solve_entry_tips(graph, starting_nodes)
    return graph

        
def solve_out_tips(graph, ending_nodes):
    for node in graph.nodes():
        path_list,path_length,weight_avg_list= [],[],[]        
        tips = False
        list_successors = list(graph.successors(node))
        if len(list_successors) > 1:
            for end in ending_nodes:
                if nx.has_path(graph,node,end):
                    path = list(nx.all_simple_paths(
                        graph, node,end))
                    path_list.append(path[0])
                    path_length.append(len(path[0]))
                    weight_avg_list.append(path_average_weight(graph, path[0]))
                    tips = True
                
        if tips:
            break
    if tips:
        graph = select_best_path(
            graph, path_list, path_length, weight_avg_list, delete_sink_node=True)
        graph = solve_out_tips(graph, ending_nodes)
    return graph

def get_starting_nodes(graph):
    first_node=[]
    for n in graph.nodes : 
        if len(list(graph.predecessors(n)))==0: 
            first_node.append(n)
    return first_node

def get_sink_nodes(graph):
    last_node=[]
    for n in graph.nodes : 
        if len(list(graph.successors(n)))==0: 
            last_node.append(n)
    return last_node
    

def get_contigs(graph, starting_nodes, ending_nodes):
    contigs = []
    for start in starting_nodes : 
        for end in ending_nodes : 
         if nx.has_path(graph,start,end):
            seq=""
            for path in nx.all_simple_paths(graph,start,end): 
                seq+=path[0]
                for kmer in path[1:]: 
                    seq+=kmer[-1]
                contigs.append((seq,len(seq)))    
       
    return contigs        
        
       
def save_contigs(contigs_list, output_file):
    with open(output_file,"w") as file:
        for contigs in contigs_list:
            file.write(">contig_{0} len={1} \n".format(contigs[0],contigs[1]))
            file.write(textwrap.fill(contigs[0], width=80)+"\n")

def draw_graph(graph, graphimg_file):
    """Draw the graph
    """                                    
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] > 3]
    #print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d['weight'] <= 3]
    #print(elarge)
    # Draw the graph with networkx
    #pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(graph, pos, edgelist=esmall, width=6, alpha=0.5, 
                           edge_color='b', style='dashed')
    #nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file)


#==============================================================
# Main program
#==============================================================
def main():
    """
    Main program function
    """
    # Get arguments
    args = get_arguments()
    # 1. Lecture du fichier et construction du graphe
    kmer_dict =build_kmer_dict(args.fastq_file,args.kmer_size)
    graph = build_graph(kmer_dict)

    # 2. R??solution des bulles
    graph = simplify_bubbles(graph)

    # 3. R??solution des pointes d???entr??e et de sortie
    
    graph = solve_entry_tips(graph,get_starting_nodes(graph))
    graph = solve_out_tips(graph,get_sink_nodes(graph))
    # 4. Ecriture du/des contigs 
    contigs = get_contigs(graph,get_starting_nodes(graph),get_sink_nodes(graph))
    save_contigs(contigs,args.output_file)
 


    # Fonctions de dessin du graphe
    # A decommenter si vous souhaitez visualiser un petit 
    # graphe
    # Plot the graph
    if args.graphimg_file:
         draw_graph(graph, args.graphimg_file)


if __name__ == '__main__':
    main()
