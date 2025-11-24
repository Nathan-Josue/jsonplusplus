"""
Interface en ligne de commande (CLI) pour jsonplusplus.
"""

import argparse
import json
import sys
import os
from pathlib import Path
from . import (
    jonx_encode,
    encode_to_bytes,
    decode_from_bytes,
    JONXFile,
    JONXError,
    JONXValidationError,
    JONXEncodeError,
    JONXDecodeError,
    JONXFileError
)


def cmd_encode(args):
    """Commande pour encoder JSON → JONX"""
    try:
        # Lire le fichier JSON
        if not os.path.exists(args.input):
            print(f"❌ Erreur: Le fichier '{args.input}' n'existe pas", file=sys.stderr)
            sys.exit(1)
        
        # Déterminer le fichier de sortie
        if args.output:
            output_path = args.output
        else:
            # Générer automatiquement le nom de sortie
            input_path = Path(args.input)
            output_path = input_path.with_suffix('.jonx')
        
        # Encoder
        print(f"📦 Encodage de '{args.input}' vers '{output_path}'...")
        jonx_encode(args.input, output_path)
        
        # Afficher les statistiques
        input_size = os.path.getsize(args.input)
        output_size = os.path.getsize(output_path)
        compression_ratio = (1 - output_size / input_size) * 100 if input_size > 0 else 0
        
        print(f"✅ Encodage réussi!")
        print(f"   Taille originale: {input_size:,} bytes")
        print(f"   Taille JONX: {output_size:,} bytes")
        print(f"   Compression: {compression_ratio:.1f}%")
        
    except JONXError as e:
        print(f"❌ Erreur JONX: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_decode(args):
    """Commande pour décoder JONX → JSON"""
    try:
        if not os.path.exists(args.input):
            print(f"❌ Erreur: Le fichier '{args.input}' n'existe pas", file=sys.stderr)
            sys.exit(1)
        
        # Déterminer le fichier de sortie
        if args.output:
            output_path = args.output
        else:
            input_path = Path(args.input)
            output_path = input_path.with_suffix('.json')
        
        # Décoder
        print(f"📦 Décodage de '{args.input}' vers '{output_path}'...")
        
        with open(args.input, "rb") as f:
            jonx_bytes = f.read()
        
        result = decode_from_bytes(jonx_bytes)
        
        # Écrire le JSON
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result["json_data"], f, indent=2, ensure_ascii=False)
        
        print(f"✅ Décodage réussi!")
        print(f"   Version: {result['version']}")
        print(f"   Lignes: {result['num_rows']}")
        print(f"   Colonnes: {len(result['fields'])}")
        print(f"   Fichier créé: {output_path}")
        
    except JONXError as e:
        print(f"❌ Erreur JONX: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_info(args):
    """Commande pour afficher les informations d'un fichier JONX"""
    try:
        if not os.path.exists(args.file):
            print(f"❌ Erreur: Le fichier '{args.file}' n'existe pas", file=sys.stderr)
            sys.exit(1)
        
        jonx_file = JONXFile(args.file)
        info = jonx_file.info()
        
        print(f"\n📊 Informations sur '{args.file}':")
        print("=" * 60)
        print(f"Chemin:           {info['path']}")
        print(f"Version:          {info['version']}")
        print(f"Nombre de lignes: {info['num_rows']:,}")
        print(f"Nombre de colonnes: {info['num_columns']}")
        print(f"Taille du fichier: {info['file_size']:,} bytes")
        
        print(f"\nColonnes ({len(info['fields'])}):")
        for field in info['fields']:
            col_type = info['types'][field]
            has_idx = "✓" if field in info['indexes'] else " "
            print(f"  [{has_idx}] {field:20s} ({col_type})")
        
        if info['indexes']:
            print(f"\nIndex disponibles ({len(info['indexes'])}):")
            for idx in info['indexes']:
                print(f"  - {idx}")
        
        print()
        
    except JONXError as e:
        print(f"❌ Erreur JONX: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_validate(args):
    """Commande pour valider un fichier JONX"""
    try:
        if not os.path.exists(args.file):
            print(f"❌ Erreur: Le fichier '{args.file}' n'existe pas", file=sys.stderr)
            sys.exit(1)
        
        print(f"🔍 Validation de '{args.file}'...")
        jonx_file = JONXFile(args.file)
        validation = jonx_file.validate()
        
        if validation["valid"]:
            print("✅ Fichier valide!")
            if validation["warnings"]:
                print(f"\n⚠️  Avertissements ({len(validation['warnings'])}):")
                for warning in validation["warnings"]:
                    print(f"  - {warning}")
        else:
            print("❌ Fichier invalide!")
            print(f"\nErreurs ({len(validation['errors'])}):")
            for error in validation["errors"]:
                print(f"  - {error}")
            if validation["warnings"]:
                print(f"\n⚠️  Avertissements ({len(validation['warnings'])}):")
                for warning in validation["warnings"]:
                    print(f"  - {warning}")
            sys.exit(1)
        
    except JONXError as e:
        print(f"❌ Erreur JONX: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_query(args):
    """Commande pour interroger un fichier JONX"""
    try:
        if not os.path.exists(args.file):
            print(f"❌ Erreur: Le fichier '{args.file}' n'existe pas", file=sys.stderr)
            sys.exit(1)
        
        jonx_file = JONXFile(args.file)
        
        # Vérifier que la colonne existe
        if args.column not in jonx_file.fields:
            print(f"❌ Erreur: La colonne '{args.column}' n'existe pas", file=sys.stderr)
            print(f"Colonnes disponibles: {', '.join(jonx_file.fields)}", file=sys.stderr)
            sys.exit(1)
        
        # Exécuter la requête
        if args.operation == "min":
            value = jonx_file.find_min(args.column, use_index=args.use_index)
            print(f"Minimum de '{args.column}': {value}")
        
        elif args.operation == "max":
            value = jonx_file.find_max(args.column, use_index=args.use_index)
            print(f"Maximum de '{args.column}': {value}")
        
        elif args.operation == "sum":
            if not jonx_file.is_numeric(args.column):
                print(f"❌ Erreur: La colonne '{args.column}' n'est pas numérique", file=sys.stderr)
                sys.exit(1)
            value = jonx_file.sum(args.column)
            print(f"Somme de '{args.column}': {value}")
        
        elif args.operation == "avg":
            if not jonx_file.is_numeric(args.column):
                print(f"❌ Erreur: La colonne '{args.column}' n'est pas numérique", file=sys.stderr)
                sys.exit(1)
            value = jonx_file.avg(args.column)
            print(f"Moyenne de '{args.column}': {value}")
        
        elif args.operation == "count":
            value = jonx_file.count(args.column)
            print(f"Nombre d'éléments dans '{args.column}': {value}")
        
    except JONXError as e:
        print(f"❌ Erreur JONX: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Point d'entrée principal du CLI"""
    parser = argparse.ArgumentParser(
        prog="jsonplusplus",
        description="JSON++ (JONX) - Format de données JSON colonné et compressé",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Encoder un fichier JSON
  jsonplusplus encode data.json -o data.jonx
  
  # Décoder un fichier JONX
  jsonplusplus decode data.jonx -o data.json
  
  # Afficher les informations
  jsonplusplus info data.jonx
  
  # Valider un fichier
  jsonplusplus validate data.jonx
  
  # Interroger un fichier
  jsonplusplus query data.jonx price --min
  jsonplusplus query data.jonx age --avg
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")
    
    # Commande encode
    encode_parser = subparsers.add_parser("encode", help="Encoder JSON → JONX")
    encode_parser.add_argument("input", help="Fichier JSON d'entrée")
    encode_parser.add_argument("-o", "--output", help="Fichier JONX de sortie (optionnel)")
    encode_parser.set_defaults(func=cmd_encode)
    
    # Commande decode
    decode_parser = subparsers.add_parser("decode", help="Décoder JONX → JSON")
    decode_parser.add_argument("input", help="Fichier JONX d'entrée")
    decode_parser.add_argument("-o", "--output", help="Fichier JSON de sortie (optionnel)")
    decode_parser.set_defaults(func=cmd_decode)
    
    # Commande info
    info_parser = subparsers.add_parser("info", help="Afficher les informations d'un fichier JONX")
    info_parser.add_argument("file", help="Fichier JONX")
    info_parser.set_defaults(func=cmd_info)
    
    # Commande validate
    validate_parser = subparsers.add_parser("validate", help="Valider un fichier JONX")
    validate_parser.add_argument("file", help="Fichier JONX")
    validate_parser.set_defaults(func=cmd_validate)
    
    # Commande query
    query_parser = subparsers.add_parser("query", help="Interroger un fichier JONX")
    query_parser.add_argument("file", help="Fichier JONX")
    query_parser.add_argument("column", help="Nom de la colonne")
    query_parser.add_argument("--min", dest="operation", action="store_const", const="min",
                             help="Trouver la valeur minimale")
    query_parser.add_argument("--max", dest="operation", action="store_const", const="max",
                             help="Trouver la valeur maximale")
    query_parser.add_argument("--sum", dest="operation", action="store_const", const="sum",
                             help="Calculer la somme")
    query_parser.add_argument("--avg", dest="operation", action="store_const", const="avg",
                             help="Calculer la moyenne")
    query_parser.add_argument("--count", dest="operation", action="store_const", const="count",
                             help="Compter les éléments")
    query_parser.add_argument("--use-index", action="store_true",
                             help="Utiliser l'index pour les opérations min/max")
    query_parser.set_defaults(func=cmd_query)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)


if __name__ == "__main__":
    main()

