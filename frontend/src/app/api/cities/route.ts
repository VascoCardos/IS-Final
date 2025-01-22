import { NextRequest, NextResponse } from "next/server";

interface City {
    nome: string;
    latitude: number;
    longitude: number;
    id: number;
}

let cachedCities: City[] = [];  // Definindo o tipo de cachedCities como um array de City

// Função para fazer a requisição e obter os dados
async function fetchCityData() {
    try {
        // Use o nome do serviço Docker em vez de localhost ou host.docker.internal
        const response = await fetch("http://rest-api-server:8000/api/get_locations/");
        
        // Verifica se a requisição foi bem-sucedida
        if (!response.ok) {
            throw new Error("Failed to fetch city data");
        }
        
        // Converte a resposta em JSON
        const data = await response.json();
        
        // Armazena os dados na variável
        cachedCities = data?.cities ?? [];
        console.log("City data fetched:", cachedCities);
    } catch (error) {
        console.error("Error fetching city data:", error);
    }
}


fetchCityData();

export async function POST(req: NextRequest) {
    const request_body  = await req.json()

    const city          = request_body?.search ?? ''

    const citiesToReturn = cachedCities.filter((cityItem) => 
        cityItem.nome.toLowerCase().includes(city.toLowerCase())
    );

    // Retorna os dados filtrados
    return NextResponse.json({
        data: {
            cities: citiesToReturn,
        }
    });

    const headers = {
        'content-type': 'application/json',
    }
    
    const requestBody = {
        query: `query Cities {
            cities${city.length > 0 ? `(nome: "${city}")` : ``} {
                nome
                latitude
                longitude
                id
            }
        }`
    }
    
    const options = {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
    }

    try{
        const promise = await fetch(`${process.env.GRAPHQL_API_BASE_URL}/graphql/cities/`, options)

        if(!promise.ok){
            console.log(promise.statusText)
            return NextResponse.json({status: promise.status, message: promise.statusText}, { status: promise.status }) 
        }

        const data = await promise.json()

        return NextResponse.json(data) 
    }catch(e){
        console.log(e)
        return NextResponse.json({status: 500, message: e}, { status: 500  }) 
    }
}