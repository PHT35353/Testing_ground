def main_storage():
    """Main function to run the Pipe Storage System app."""
    # Load existing pipe data
    pipe_data = load_data()

    st.title("Pipe and Landmark Storage System")
    st.subheader("Store and View Pipe and Landmark Details")

    # Fetch API data for pipes and landmarks
    api_pipes, total_distance = get_distance_values()
    landmarks = get_landmarks()

    # Integrate pipes into storage
    if api_pipes:
        integrate_api_data(pipe_data, api_pipes)
        st.success("Fetched and integrated pipe data from API successfully!")
        st.write(f"Total Pipe Distance from API: {total_distance} meters")

    # Add landmarks to the storage
    if landmarks:
        for landmark in landmarks:
            landmark_name = landmark["name"]
            if landmark_name not in pipe_data:  # Avoid duplicate entries
                pipe_data[landmark_name] = {
                    "coordinates": landmark["coordinates"],
                    "length": 0,  # Landmarks don't have a length
                    "medium": "N/A",  # Not applicable for landmarks
                }

    # Save updated storage
    save_data(pipe_data)

    # Display stored pipes and landmarks
    st.header("Stored Pipes and Landmarks")
    if pipe_data:
        # Prepare the table data for display
        table_data = []
        for name, details in pipe_data.items():
            # Format the name based on the type of entry
            if "length" in details and details["length"] > 0:
                # If it's a pipe, associate it with landmarks using a proximity threshold
                start_coord = details["coordinates"][0]
                end_coord = details["coordinates"][-1]

                def find_closest_landmark(coord, landmarks, threshold=0.01):
                    """Find the closest landmark to a given coordinate."""
                    for landmark in landmarks:
                        landmark_coord = landmark["coordinates"]
                        distance = ((landmark_coord[0] - coord[0]) ** 2 + (landmark_coord[1] - coord[1]) ** 2) ** 0.5
                        if distance <= threshold:
                            return landmark["name"]
                    return "Unknown"

                start_landmark = find_closest_landmark(start_coord, landmarks)
                end_landmark = find_closest_landmark(end_coord, landmarks)

                formatted_name = f"Line {name} belongs to {start_landmark} - {end_landmark}"
            else:
                # For landmarks or other entries without length, use the name as-is
                formatted_name = name

            # Add the formatted entry to the table data
            table_data.append(
                {
                    "Name": formatted_name,
                    "Coordinates": str(details["coordinates"]) if details["coordinates"] else "N/A",
                    "Length (meters)": details.get("length", 0),
                    "Medium": details.get("medium", "Not assigned"),
                }
            )

        # Convert table data to a DataFrame
        df = pd.DataFrame(table_data)
        st.subheader("Pipe and Landmark Data (Table View)")
        st.table(df)

        # Add a download button for the table
        csv_data = io.StringIO()
        df.to_csv(csv_data, index=False)
        st.download_button(
            label="Download Table as CSV",
            data=csv_data.getvalue(),
            file_name="pipe_and_landmark_data.csv",
            mime="text/csv"
        )

        # Delete a pipe or landmark by name
        st.header("Delete an Entry")
        with st.form("delete_entry_form"):
            name_to_delete = st.text_input("Name to Delete", placeholder="Enter name")
            delete_submitted = st.form_submit_button("Delete")

            if delete_submitted:
                if name_to_delete:
                    if delete_pipe(pipe_data, name_to_delete):
                        st.success(f"Entry '{name_to_delete}' deleted successfully!")
                    else:
                        st.error(f"Entry '{name_to_delete}' not found.")
                else:
                    st.error("Name is required to delete an entry.")
    else:
        st.info("No data stored yet. Add pipes or landmarks to get started.")

    # Refresh data
    if st.button("Refresh Data"):
        pipe_data.clear()
        save_data(pipe_data)
        st.warning("All data has been refreshed.")
