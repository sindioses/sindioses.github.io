SELECT id,
       message,
       length(message) as long,
       created_time,
       author,
       category,
       slug,
       permalink_url,
       json_extract(raw_json, '$.attachments.data[0].media.image.src') as image,
       raw_json
FROM posts
WHERE 1=1
    AND message is not null
    AND length(message) > 2000
    AND (author is null or category is null or slug is null)
--    AND author || category || slug is not null
ORDER BY created_time;

update posts set author = 'Iván González Mairena'
where message like '%[Godless Freeman]%' and author is null
