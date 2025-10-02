import { getLatestApiKey, getUser } from "@/app/db";
import { NextResponse } from "next/server";
import { userOperationHandler } from "@/app/lib/userOperationHandler"

export async function POST(request: Request) {
    const body: {
        orgId: string;
        trainingId: string;
        huggingFaceId: string;
        numSessions: bigint;
        telemetryEnabled: boolean;
        gitRef: string;
    } = await request.json().catch((err) => {
        console.error(err);
        console.log(body);

        return NextResponse.json(
            { error: " bad request generic " },
            { status: 400 },
        );
    })

    console.log("body", JSON.stringify(body, null, 2));

    if (!body.orgId) {
        return NextResponse.json(
            { error: " bad request orgId " },
            { status: 400 },
        );
    }

    try {
        const user = getUser(body.orgId);
        if (!user) {
            return NextResponse.json(
                { error: " user not found " },
                { status: 404 },
            );
        }

        const apiKey = getLatestApiKey(body.orgId);
        console.log("API Key retrieved:", apiKey ? { activated: apiKey.activated, hasFields: apiKey.activated ? !!apiKey.accountAddress : false } : "null");

        if (!apiKey?.activated) {
            return NextResponse.json(
                { error: " api key not found or not activated " },
                { status: 500 },
            );
        }

        const { accountAddress, privateKey, initCode, deferredActionDigest } = apiKey;

        // Validate that all required fields are present
        if (!accountAddress || !privateKey || !initCode || !deferredActionDigest) {
            console.error("Missing required API key fields:", { accountAddress, privateKey, initCode, deferredActionDigest });
            return NextResponse.json(
                { error: " api key missing required fields " },
                { status: 500 },
            );
        }

        console.log("API Key fields:", {
            accountAddress,
            privateKey: privateKey ? "present" : "missing",
            initCode,
            deferredActionDigest
        });

        console.log("Function args:", {
            accountAddress,
            trainingId: body.trainingId,
            huggingFaceId: body.huggingFaceId,
            numSessions: body.numSessions,
            telemetryEnabled: body.telemetryEnabled,
            gitRef: body.gitRef
        });

        const userOperationResponse = await userOperationHandler({
            accountAddress,
            privateKey,
            deferredActionDigest,
            initCode,
            functionName: "submitHFUploadWithRef",
            args: [accountAddress, body.trainingId, body.huggingFaceId, body.gitRef, body.numSessions, body.telemetryEnabled],
        });

        return userOperationResponse;
    } catch (err) {
        console.error(err);

        return NextResponse.json(
            { error: "An unexpected error occurred", original: err },
            { status: 500 },
        );
    }
}