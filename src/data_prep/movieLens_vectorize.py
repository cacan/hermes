import numpy as np

class movieLens_vectorize():

    def __init__(self, user_interactions, content, user_vector_type, content_vector_type, sqlCtx, **support_files ):
        """
        Class initializer to load the required files

        Args:
            user_interactions: The raw RDD of the user interactions. For MovieLens, these are the ratings
            content: The raw RDD containing the item content. For MovieLens, this is the movie categories
            user_vector_type: The type of user vector desired.  For MovieLens you can choose between ['ratings', 'pos_ratings', 'ratings_to_interact', 'none'].
                If 'none' is used then this means you will run your own custom mapping
            content_vector_type: The type of content vector desired. For MovieLens you can choose between ['genre', 'tags', 'none'].
                If none is chosen no content vector will be returned and None may be passed into the content argument.
                You do not need a content vector to run pure CF only but some performance metrics will not be able to be ran
            support_files: If they exist, the supporting files, dataFrames, and/or file links necessary to run the content vectors.
                To generate a content vector on tags, you must pass in the tag RDD as support_files['tag_rdd']
                You may also pass in the number of tags to utilize as support_files['num_tags'].  Otherwise default is set to 300


        """
        self.user_vector_type = user_vector_type
        self.content_vector_type = content_vector_type

        #Filter out uninteresting articles and users if they still exist in the dataset
        self.user_interactions =user_interactions
        self.user_interactions.registerTempTable("ratings")
        self.content = content
        self.content.registerTempTable("content")

        self.sqlCtx = sqlCtx

        #if no support files were passed in, initialize an empty support file
        if support_files:
            self.support_files = support_files
        else:
            self.support_files = {}


    def get_user_vector(self):

        if self.user_vector_type=='ratings':
            user_info = self.user_interactions.map(lambda row: (row.user_id, row.movie_id, row.rating) )
            return user_info

        elif self.user_vector_type=='pos_ratings':
            user_info = self.user_interactions.map(lambda row: (row.user_id, row.movie_id, row.rating) ).filter(lambda (u,m,r): r>3)
            return user_info

        elif self.user_vector_type=='ratings_to_interact':
            user_info = self.user_interactions.map(lambda row: (row.user_id, row.movie_id, rating_to_interaction(row.rating)) )
            return user_info

        elif self.user_vector_type=='none':
            return None

        else:
            print "Please choose a user_vector_type between 'ratings', 'pos_ratings', 'ratings_to_interact', and 'none'"
            return None

    def get_content_vector(self):

        if self.content_vector_type=='genre':
            content_array = self.content.map(lambda row: (row.movie_id, genre_vectorizer(row)))
            return content_array

        elif self.content_vector_type=='tags':
            if "tag_rdd" in self.support_files:
                tag_rdd = self.support_files['tag_rdd']
                tag_rdd.registerTempTable('tags')

                #having the user pass in the nubmer of tags is not required but optional.  Default set to
                if "num_tags" in self.support_files:
                    num_tags = self.support_files['num_tags']
                else:
                    num_tags = 300

                #get the top tags based on frequency
                tag_freq = self.sqlCtx.sql("select tag, count(*) as t_count from tags group by tag").collect()
                top_tags = sorted(tag_freq, key=lambda x: x[1], reverse=True)[:num_tags]

                #get the top tags into a pretty list
                tag_list = []
                for elem in top_tags:
                    tag_list.append(elem[0])

                tag_content =tag_rdd.map(lambda row:(row.movie_id, row.tag)).groupByKey().map(lambda row: get_tag_vect(row, tag_list))

                #instead of just having the tags - we really want to join this with the content.  Mostly because more items will have content.
                content_array = self.content.map(lambda row: (row.movie_id, genre_vectorizer(row)))

                #join the tag content and the content_array
                joined_content = content_array.leftOuterJoin(tag_content)\
                    .map(lambda (mid, (genre, tags)): (mid, list(genre)+tag_vect(tags, num_tags)))


                return joined_content
            else:
                print "Please pass in a tag RDD. Like: support_files['tag_rdd'] = sqlCtx.read.json('movielens_20m_tags.json.gz')"

        elif self.content_vector_type=='none':
            return None

        else:
            print "Please choose a content_vector_type between 'genre', 'tags', or 'none'"
            return None



def rating_to_interaction(rating):
    if rating<3:
        return -1
    else:
        return 1

def get_tag_vect(row, keeper_tags):
    tag_vect = np.zeros(len(keeper_tags))
    for tag in row[1]:
        try:
            index = keeper_tags.index(tag)
            tag_vect[index] = 1
        except:
            pass
    return (row[0], tag_vect)

def tag_vect(tags, num_tags):
    if tags is None:
        return list(np.zeros(num_tags))
    else:
        return list(tags)

def genre_vectorizer(row):
    return np.array((
            int(row.genre_action),
            int(row.genre_adventure),
            int(row.genre_animation),
            int(row.genre_childrens),
            int(row.genre_comedy),
            int(row.genre_crime),
            int(row.genre_documentary),
            int(row.genre_drama),
            int(row.genre_fantasy),
            int(row.genre_filmnoir),
            int(row.genre_horror),
            int(row.genre_musical),
            int(row.genre_mystery),
            int(row.genre_romance),
            int(row.genre_scifi),
            int(row.genre_thriller),
            int(row.genre_war),
            int(row.genre_western),
        ))