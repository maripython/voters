import os


def process_text_files(output_path):
    data_to_insert = []  # Initialize a list to store data for insertion
    for root, dirs, files in os.walk(output_path):
        for file in files:
            if file.endswith(".txt"):  # Process only text files
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    page_one_text = f.read()
                    detail = page_one_text.split(" ")
                    part_no = ""
                    village = ""
                    ward = ""
                    post_office = ""
                    police_station = ""
                    block = ""
                    subdivision = ""
                    division = ""
                    district = ""
                    pin_code = ""

                    found_first_occurrence = False
                    first_occurrence = False
                    for item in detail:
                        item = item.strip(':')
                        if "நகரம்/கிராமம்" in item or "நகரம்கிராமம்" in item:
                            village_index = detail.index(item) + 1
                            if village_index < len(detail):
                                village = detail[village_index]
                            else:
                                village = None

                        if "அலுவலகம்" in item:
                            post_office = detail[detail.index(item) + 2]

                        if "நிலையம்" in item:
                            station_index = detail.index(item) + 1
                            if station_index + 2 < len(detail):
                                police_station = ' '.join(detail[station_index:station_index + 2])
                            else:
                                police_station = None

                        elif "பஞ்சாயத்து" in item:
                            block_index = detail.index(item) + 1
                            if block_index < len(detail):
                                block = detail[block_index]
                            else:
                                block = None

                        elif "கோட்டம்" in item:
                            division = detail[detail.index(item) + 1]

                        elif "மாவட்டம்" in item:
                            district = detail[detail.index(item) + 2]

                        elif "வட்டம்" in item:
                            subdivision = detail[detail.index(item) + 1]

                        elif "குறியீட்டு" in item:
                            pin_code = detail[detail.index(item) + 3]

                        if "பாகம்" in item:
                            if found_first_occurrence:
                                continue
                            item_index = detail.index(item)
                            part_no = detail[item_index + 2]
                            found_first_occurrence = True
                        if "சட்டமன்றத்" in item:
                            if first_occurrence:
                                continue
                            if "பாகம்" not in detail:
                                name_of_assembly_constituency = ""
                            else:
                                item_index = detail.index(item)
                                if "பாகம்" in detail[item_index:]:
                                    name_of_assembly_constituency = ' '.join(
                                        detail[item_index + 9: detail.index("பாகம்")])
                                    first_occurrence = True
                                else:
                                    name_of_assembly_constituency = ""

                    data_dict = {
                        "பாகம் எண்": part_no,
                        "சட்டமன்றத் தொகுதியின் பெயர்": name_of_assembly_constituency,
                        "நகரம் / கிராமம்": village,
                        "வார்டு": ward,
                        "அஞ்சல் அலுவலகம்": post_office,
                        "காவல் நிலையம்": police_station,
                        "பஞ்சாயத்து": block,
                        "வட்டம்": subdivision,
                        "கோட்டம்": division,
                        "மாவட்டம்": district,
                        "அஞ்சல் குறியீட்டு எண்": pin_code
                    }
                    data_to_insert.append(data_dict)  # Add the data_dict to the list for insertion
                    print(data_to_insert)
    mapping = {
        "பாகம் எண்": "part_no",
        "நகரம் / கிராமம்": "village",
        "வார்டு": "ward",
        "அஞ்சல் அலுவலகம்": "post_office",
        "காவல் நிலையம்": "police_station",
        "பஞ்சாயத்து": "block",
        "வட்டம்": "subdivision",
        "கோட்டம்": "division",
        "மாவட்டம்": "district",
        "அஞ்சல் குறியீட்டு எண்": "pin_code",
        "pdf_name": "pdf_name"
    }
    # Rename keys for all dictionaries in the list
    # data_to_insert = [{mapping.get(old_key, old_key): value for old_key, value in data.items()} for data in
    #                   data_to_insert]
    #
    # collection_name = "first_page_data"  # You can use the subfolder name as the collection name
    # collection = db[collection_name]
    # collection.insert_many(data_to_insert)  # Use insert_many to insert all data_dict documents at once
    #
    # print(f"{len(data_to_insert)} data entries saved to MongoDB collection '{collection_name}'")
    # print(f"{data_to_insert} data entries saved to MongoDB collection '{collection_name}'")
    return data_dict


process_text_files("first_page_data")
