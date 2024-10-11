# data_loader.py

import pandas as pd
import csv
import re
import chardet

class DataLoader:
    def detect_encoding(self, filepath):
        """
        Detects the encoding of the file using chardet.
        If detection fails, defaults to 'utf-8'.
        """
        try:
            with open(filepath, 'rb') as f:
                raw_data = f.read(10000)  # Read first 10,000 bytes
                result = chardet.detect(raw_data)
                encoding = result['encoding']
                # Uncomment for debugging: print(f"Detected encoding: {encoding}")
                if encoding:
                    return encoding
                else:
                    print("Encoding detection failed, defaulting to 'utf-8'.")
                    return 'utf-8'
        except Exception as e:
            print(f"Error detecting encoding: {e}")
            return 'utf-8'

    def detect_delimiter(self, filepath, encoding):
        """
        Automatically detects the delimiter in the given file using csv.Sniffer.
        If detection fails, defaults to tab or comma based on common patterns.
        """
        try:
            with open(filepath, 'r', newline='', encoding=encoding) as csvfile:
                sample = csvfile.read(1024)
                sniffer = csv.Sniffer()
                dialect = sniffer.sniff(sample, delimiters=[',', ';', '\t', '|'])
                delimiter = dialect.delimiter
                # Uncomment for debugging: print(f"Detected delimiter: '{delimiter}'")
                return delimiter
        except Exception as e:
            # If delimiter detection fails, check for tabs or commas manually
            with open(filepath, 'r', encoding=encoding) as f:
                first_line = f.readline()
                if '\t' in first_line:
                    delimiter = '\t'
                elif ',' in first_line:
                    delimiter = ','
                else:
                    delimiter = ','  # Default to comma
            print(f"Could not detect delimiter using csv.Sniffer, defaulting to '{delimiter}'. Error: {e}")
            return delimiter

    def extract_base_name(self, column_name):
        """
        Extracts the base name from a column by removing any text within brackets or parentheses.
        Handles multiple brackets/parentheses and nested cases.
        """
        # Remove any content within parentheses, brackets, or braces
        base_name = re.sub(r'\s*[\(\[\{][^\)\]\}]*[\)\]\}]\s*', '', column_name)
        return base_name.strip()

    def load_xyc(self, filepath):
        """
        Loads data from a delimited file, detects the encoding and delimiter, and extracts
        the Time, R, and Concentration columns. If the Concentration column is missing,
        it sets it to zero.

        Parameters:
            filepath (str): Path to the delimited file.

        Returns:
            dict: Dictionary containing:
                - 'x': Time data
                - 'y': R data
                - 'c': Concentration data (zeros if not present)
                - 'xlabel': Original Time column name with units
                - 'ylabel': Original R column name with units
                - 'zlabel': Original Concentration column name with units or 'Concentration [unit]'
        """
        try:
            # Detect the encoding
            encoding = self.detect_encoding(filepath)
            # Uncomment for debugging: print(f"Using encoding: {encoding}")

            # Detect the delimiter
            delimiter = self.detect_delimiter(filepath, encoding)

            # Read the file with pandas using the detected delimiter and encoding
            df = pd.read_csv(filepath, delimiter=delimiter, encoding=encoding)
            # Uncomment for debugging: print(f"Columns found in data: {list(df.columns)}")

            # Initialize dictionary to hold column mappings
            column_mapping = {}

            # Define possible base names for required columns
            base_names = {
                'time': ['time'],
                'r': ['r', 'resistance'],
                'concentration': ['concentration', 'conc', 'c']
            }

            # Iterate over columns to find the required ones
            for col in df.columns:
                base_name = self.extract_base_name(col).lower()
                # Uncomment for debugging: print(f"Processing column '{col}', base name '{base_name}'")
                for key, aliases in base_names.items():
                    if base_name == key or base_name in aliases:
                        column_mapping[key] = col  # Map the key to the actual column name
                        break

            # Check for required columns 'time' and 'r'
            required = ['time', 'r']
            missing = [col for col in required if col not in column_mapping]
            if missing:
                raise ValueError(f"Required columns {missing} not found in the data.")

            # Extract data
            x = df[column_mapping['time']].values
            y = df[column_mapping['r']].values

            # Check if 'concentration' column is present
            if 'concentration' in column_mapping:
                c = df[column_mapping['concentration']].values
                zlabel = column_mapping['concentration']
            else:
                # Set Concentration to zero if not present
                c = pd.Series([0] * len(x)).values
                zlabel = 'Concentration [null]'  # Placeholder label

            # Extract labels with units
            xlabel = column_mapping['time']
            ylabel = column_mapping['r']

            return {
                'x': x,
                'y': y,
                'c': c,
                'xlabel': xlabel,
                'ylabel': ylabel,
                'zlabel': zlabel
            }

        except UnicodeDecodeError as e:
            print(f"UnicodeDecodeError: {e}")
            # Try common encodings if initial encoding fails
            for enc in ['cp1250', 'latin1', 'utf-8']:
                try:
                    print(f"Attempting to read file with encoding: {enc}")
                    df = pd.read_csv(filepath, delimiter=delimiter, encoding=enc)
                    # Repeat the column mapping and data extraction as before
                    # ... (same as above)
                    # Since we're in a new try-except, copy the code from above

                    # Initialize dictionary to hold column mappings
                    column_mapping = {}

                    # Iterate over columns to find the required ones
                    for col in df.columns:
                        base_name = self.extract_base_name(col).lower()
                        for key, aliases in base_names.items():
                            if base_name == key or base_name in aliases:
                                column_mapping[key] = col  # Map the key to the actual column name
                                break

                    # Check for required columns 'time' and 'r'
                    required = ['time', 'r']
                    missing = [col for col in required if col not in column_mapping]
                    if missing:
                        raise ValueError(f"Required columns {missing} not found in the data.")

                    # Extract data
                    x = df[column_mapping['time']].values
                    y = df[column_mapping['r']].values

                    # Check if 'concentration' column is present
                    if 'concentration' in column_mapping:
                        c = df[column_mapping['concentration']].values
                        zlabel = column_mapping['concentration']
                    else:
                        # Set Concentration to zero if not present
                        c = pd.Series([0] * len(x)).values
                        zlabel = 'Concentration [null]'  # Placeholder label

                    # Extract labels with units
                    xlabel = column_mapping['time']
                    ylabel = column_mapping['r']

                    return {
                        'x': x,
                        'y': y,
                        'c': c,
                        'xlabel': xlabel,
                        'ylabel': ylabel,
                        'zlabel': zlabel
                    }
                except UnicodeDecodeError:
                    continue  # Try the next encoding
                except Exception as e:
                    print(f"Error loading data with encoding {enc}: {e}")
                    return None
            print("Failed to read the file with common encodings.")
            return None
        except Exception as e:
            print(f"Error loading data: {e}")
            return None