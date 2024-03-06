forward_list = "1,2,3,4,"
forward_links = forward_list.split(',')
for forward_link_id in forward_links:
    if forward_link_id is not None:
        print(forward_link_id)
print(forward_links)
