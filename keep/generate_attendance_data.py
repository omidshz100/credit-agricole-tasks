import random
import datetime
from datetime import timedelta
import csv

def generate_attendance_data():
    """
    Generate attendance data for all specified IDs for weekdays (Monday-Friday) over 3 years
    """
    
    # List of all IDs from the requirements
    employee_ids = [
        3, 7, 12, 18, 25, 31, 39, 44, 52, 58, 63, 71, 77, 84, 92, 99, 105, 112, 118, 126,
        133, 141, 149, 156, 163, 171, 178, 185, 193, 201, 208, 215, 223, 231, 239, 246,
        254, 262, 269, 277, 285, 292, 300, 308, 315, 323, 331, 338, 346, 354, 361, 369,
        377, 384, 392, 400, 407, 415, 423, 430, 438, 446, 453, 461, 469, 476, 484, 492,
        499, 507, 515, 522, 530, 538, 545, 553, 561, 568, 576, 584, 591, 599, 607, 614,
        622, 630, 637, 645, 653, 660, 668, 676, 683, 691, 699, 706, 714, 722, 729, 737
    ]
    
    # Start date (you can modify this as needed)
    start_date = datetime.date(2022, 1, 3)  # Starting from a Monday
    
    # Generate data for 3 years
    end_date = start_date + timedelta(days=3*365)
    
    attendance_data = []
    
    current_date = start_date
    
    while current_date <= end_date:
        # Check if current day is a weekday (Monday=0, Sunday=6)
        if current_date.weekday() < 5:  # Monday to Friday (0-4)
            for employee_id in employee_ids:
                # Generate random state (0 or 1)
                # You can adjust the probability here if needed
                state = random.choice([0, 1])
                
                attendance_record = {
                    'id': employee_id,
                    'date': current_date.strftime('%Y-%m-%d'),
                    'state': state
                }
                
                attendance_data.append(attendance_record)
        
        current_date += timedelta(days=1)
    
    return attendance_data

def save_to_csv(data, filename='attendance_data.csv'):
    """
    Save attendance data to CSV file
    """
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'date', 'state']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    
    print(f"Data saved to {filename}")
    print(f"Total records generated: {len(data)}")

def save_to_sql_insert(data, filename='attendance_insert.sql'):
    """
    Save attendance data as SQL INSERT statements
    """
    with open(filename, 'w', encoding='utf-8') as sqlfile:
        sqlfile.write("-- Attendance table INSERT statements\n")
        sqlfile.write("-- Generated data for 3 years of weekdays\n\n")
        
        for i, record in enumerate(data):
            if i == 0:
                sqlfile.write("INSERT INTO Attendance (id, date, state) VALUES\n")
            
            comma = "," if i < len(data) - 1 else ";"
            sqlfile.write(f"({record['id']}, '{record['date']}', {record['state']}){comma}\n")
    
    print(f"SQL INSERT statements saved to {filename}")

def print_sample_data(data, num_samples=10):
    """
    Print a sample of the generated data
    """
    print(f"\nSample of generated data (first {num_samples} records):")
    print("ID\tDate\t\tState")
    print("-" * 25)
    
    for i, record in enumerate(data[:num_samples]):
        print(f"{record['id']}\t{record['date']}\t{record['state']}")
    
    print(f"\n... and {len(data) - num_samples} more records")

def main():
    """
    Main function to generate and save attendance data
    """
    print("Generating attendance data...")
    print("Parameters:")
    print("- Period: 3 years of weekdays (Monday to Friday)")
    print("- IDs: 98 employee IDs as specified")
    print("- State: Random values 0 or 1")
    print("- Date format: YYYY-MM-DD")
    print()
    
    # Generate the data
    attendance_data = generate_attendance_data()
    
    # Print sample data
    print_sample_data(attendance_data)
    
    # Save to CSV
    csv_filename = 'attendance_data.csv'
    save_to_csv(attendance_data, csv_filename)
    
    # Save to SQL
    sql_filename = 'attendance_insert.sql'
    save_to_sql_insert(attendance_data, sql_filename)
    
    # Print statistics
    print(f"\nStatistics:")
    print(f"Number of employees: {len(set(record['id'] for record in attendance_data))}")
    print(f"Date range: {min(record['date'] for record in attendance_data)} to {max(record['date'] for record in attendance_data)}")
    print(f"Total working days covered: {len(set(record['date'] for record in attendance_data))}")
    print(f"Total attendance records: {len(attendance_data)}")

if __name__ == "__main__":
    # Set random seed for reproducible results (optional)
    random.seed(42)
    
    main()