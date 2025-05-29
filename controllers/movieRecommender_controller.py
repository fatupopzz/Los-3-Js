from neo4j_connection import Neo4jConnection

class MovieRecommenderController:
    @staticmethod
    def get_recommendations_for_user(user_id, limit=10):
        """Algoritmo simplificado de recomendaciones"""
        
        # Primero intentar recomendaciones basadas en preferencias
        query = """
        MATCH (u:User {id: $user_id})
        
        // Obtener preferencias de género del usuario
        OPTIONAL MATCH (u)-[pg:USER_GENRE_PREFERENCE]->(g:Genre)
        WITH u, COLLECT({genre: g.name, peso: pg.peso}) AS user_genres
        
        // Buscar películas que no ha visto
        MATCH (m:Movie)
        WHERE NOT EXISTS((u)-[:INTERACTED]->(m))
        
        // Calcular puntuación basada en géneros
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(mg:Genre)
        WITH m, user_genres, COLLECT(DISTINCT mg.name) AS movie_genres
        
        // Calcular score simple
        WITH m, movie_genres,
             REDUCE(score = 0.0, user_pref IN user_genres |
               CASE WHEN user_pref.genre IN movie_genres 
                    THEN score + user_pref.peso 
                    ELSE score 
               END
             ) AS preference_score
        
        // Solo películas con score > 0
        WHERE preference_score > 0
        
        // Obtener información completa de la película
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
        OPTIONAL MATCH (m)-[:HAS_ACTOR]->(a:Actor)
        OPTIONAL MATCH (m)-[:DIRECTED_BY]->(d:Director)
        
        RETURN {
            id: m.id,
            title: m.title,
            year: m.year,
            score: round(preference_score * 100) / 100,
            genres: COLLECT(DISTINCT g.name)[0..3],
            actors: COLLECT(DISTINCT a.name)[0..2],
            director: COLLECT(DISTINCT d.name)[0],
            recommendation_type: 'content_based'
        } AS movie
        ORDER BY preference_score DESC
        LIMIT $limit
        """
        
        try:
            with Neo4jConnection() as conn:
                print(f"DEBUG >> Buscando recomendaciones para usuario: {user_id}")
                result = conn.query(query, {"user_id": user_id, "limit": limit})
                print(f"DEBUG >> Recomendaciones encontradas: {len(result)}")
                
                if result:
                    print(f"DEBUG >> Primera recomendación: {result[0]}")
                    # Extraer solo la parte 'movie' de cada resultado
                    movies = [item['movie'] for item in result if 'movie' in item]
                    return movies
                else:
                    print(f"DEBUG >> No hay recomendaciones basadas en preferencias, usando películas populares")
                    return MovieRecommenderController._get_popular_movies(user_id, limit)
                    
        except Exception as e:
            print(f"ERROR >> En get_recommendations_for_user: {str(e)}")
            return MovieRecommenderController._get_popular_movies(user_id, limit)

    @staticmethod
    def _get_popular_movies(user_id, limit):
        """Fallback: películas populares que no ha visto"""
        query = """
        MATCH (u:User {id: $user_id})
        MATCH (m:Movie)
        WHERE NOT EXISTS((u)-[:INTERACTED]->(m))
        
        // Obtener información completa
        OPTIONAL MATCH (m)-[:HAS_GENRE]->(g:Genre)
        OPTIONAL MATCH (m)-[:HAS_ACTOR]->(a:Actor)
        OPTIONAL MATCH (m)-[:DIRECTED_BY]->(d:Director)
        
        // Calcular popularidad simple (por número de géneros/actores)
        WITH m, 
             COUNT(DISTINCT g) + COUNT(DISTINCT a) + COUNT(DISTINCT d) AS popularity_score,
             COLLECT(DISTINCT g.name)[0..3] AS genres,
             COLLECT(DISTINCT a.name)[0..2] AS actors,
             COLLECT(DISTINCT d.name)[0] AS director
        
        WHERE popularity_score > 0
        
        RETURN {
            id: m.id,
            title: m.title,
            year: m.year,
            score: 0.5,
            genres: genres,
            actors: actors,
            director: director,
            recommendation_type: 'popular'
        } AS movie
        
        ORDER BY popularity_score DESC, m.title
        LIMIT $limit
        """
        
        try:
            with Neo4jConnection() as conn:
                print(f"DEBUG >> Buscando películas populares para usuario: {user_id}")
                result = conn.query(query, {"user_id": user_id, "limit": limit})
                print(f"DEBUG >> Películas populares encontradas: {len(result)}")
                if result:
                    print(f"DEBUG >> Primera película popular: {result[0]}")
                    # Extraer solo la parte 'movie' de cada resultado
                    movies = [item['movie'] for item in result if 'movie' in item]
                    return movies
                return []
        except Exception as e:
            print(f"ERROR >> En _get_popular_movies: {str(e)}")
            return []

    @staticmethod
    def get_explanation_for_recommendation(user_id, movie_id):
        """Explicación simple de por qué se recomendó"""
        query = """
        MATCH (u:User {id: $user_id}), (m:Movie {id: $movie_id})
        
        OPTIONAL MATCH (u)-[pg:USER_GENRE_PREFERENCE]->(g:Genre)<-[:HAS_GENRE]-(m)
        
        RETURN {
            movie: {id: m.id, title: m.title},
            reasons: {
                matched_genres: COLLECT({genre: g.name, weight: pg.peso})
            }
        } AS explanation
        """
        
        with Neo4jConnection() as conn:
            result = conn.query(query, {"user_id": user_id, "movie_id": movie_id})
            return result[0] if result else None